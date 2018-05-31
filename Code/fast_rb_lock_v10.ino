#include <EEPROM.h>
#include <analogShield.h>
#include <math.h>
#include<SPI.h>  // SPI.h has to be included **after** analogShield.h

#define UNO_ID "rb_lock\r\n"
#define ZEROV 32768 //Zero volts
#define V2P5 49512  // 2.5 V

#define N_STEPS 800
#define N_STEPS_DOWN 800

#define STATE_NOT_SCANNING 0
#define STATE_SCANNING 1
#define STATE_AUTOSCAN 2

#define ACCUMULATOR2_MAX 3000 //was 2000 (increasing this changes how long it takes before it recognizes that the laser cannot be locked)
#define ACCUMULATOR1_MAX 100 // was 200, 400, 800 (decreasing this acrtivates auto-relock at smaller accumulator amplitudes (earlier)). 
// but making this too small can also activate this when the laser is notmally locked, this reduces the controller's ability to tighly lock and reduce fluctuations). 

#define INTEGRATOR_HOLD_TIME 1000  // microseconds, was 5000, then 1000


struct Params {
  int ramp_amplitude;
  float gain_p, gain_i, gain_ff, gain_c, gain_i2;
  int output_offset_pzt, output_offset_curr;
  int c_gain_on;
  int p_gain_on;
  int c_integrator_on;
  int p_integrator_on;
  int scan_state;
};

Params params;

int in2;
int out0, out1, out2, out3;
//out0 - piezo output
//out1 - current output
//out2 - MONITOR - pause_accumulator (check if it is still that)
//out3 - MONITOR - accumulator (check if it is still that)


bool ramp_direction;
int ramp_offset, ramp_step, ramp_step_down;
int cycle_up;
int cycle_down;
float error_signal;
float accumulator;
float accumulator2;

float in2_array[N_STEPS]; 
float out0_array[N_STEPS];

float locked_in2Total;
int lockcounter;
float in2_offsetcorrection;

float zerov_float;

bool pause_accumulator;
unsigned long pause_time;
int LPindexOffset;

void setup() {
  SPI.setClockDivider(SPI_CLOCK_DIV2);
  Serial.begin(115200);

  zerov_float = 32768.0;
  
  // put your setup code here, to run once:
  in2 = ZEROV;
  
  out0 = ZEROV;
  out1 = ZEROV;
  out2 = ZEROV;
  out3 = ZEROV;

  params.ramp_amplitude = 2400;
  params.gain_p = 40000;
  params.gain_i = 8000;
  params.gain_ff = 0.07;
  params.gain_c = 8000;
  params.gain_i2 = 0.004;
  
  params.output_offset_pzt = V2P5;
  params.output_offset_curr = ZEROV;

  params.c_gain_on = false;
  params.p_gain_on = false;

  params.c_integrator_on = false;
  params.p_integrator_on = false;
  
  accumulator = 0.0;
  accumulator2 = 0.0;
  
  params.scan_state = STATE_SCANNING;
  
  processParams();
  error_signal = 0.0;

  in2_array[N_STEPS] = {0.0}; 
  out0_array[N_STEPS] = {0.0};

  locked_in2Total = 0.010;
  lockcounter = 0;
  in2_offsetcorrection = 0.0;

  LPindexOffset = 0;

  pause_accumulator = true;
}

void resetLockedcounter(float in2_in){
  locked_in2Total = in2_in;
  lockcounter = 1;
}

void processParams() {
  ramp_direction = true;
  ramp_offset = -params.ramp_amplitude;
  ramp_step = 2*params.ramp_amplitude/N_STEPS;
  ramp_step_down = 2*params.ramp_amplitude/N_STEPS_DOWN;
  cycle_up = 0;
  cycle_down = 0;

  resetLockedcounter(0.0);
  in2_offsetcorrection = 0.0;
}

void loop() {
 
  if(Serial.available())
    parseSerial();

  // Read A2 pin from analog shield (Error signal)
  in2 = analog.read(2, false);

  //in2 += (0.017*zerov_float/5.0);

  // out0 = piezo, out1 = LD current mod, out2 = auto-relock monitor 
  out0 = ZEROV;
  out1 = ZEROV;
  out2 = ZEROV;
  //out3 = ZEROV;
  
  out0 = params.output_offset_pzt;
  float out0mod = 0.0;
  if(params.scan_state == STATE_SCANNING) {
    //standard scan - no autolocking, no offset corrections
    //resetLockedcounter(in2);
    in2_offsetcorrection = 0.0;
    runStdScan();
  } else if (params.scan_state == STATE_AUTOSCAN){
    // tries to find the lock point again
    runAutoScan();
  } else {
    // in2 offset correction (source of offset: arduino glitch). 
    //locked_in2Total += in2;
    lockcounter++;
    if (lockcounter % 10 == 0) {
      //accumulator = 0.0;
      //accumulator2 = 0.0;
      //in2_offsetcorrection = (zerov_float - locked_in2Total/((float)lockcounter));
      resetLockedcounter(in2);//locked_in2Total = in2 and lockcounter = 1
    }
    
    //in2 += in2_offsetcorrection;        // in2_offsetcorrection is reset to 0during processparams() and std. scan
  }                                     // else it is updated every 100 lock iterations

  float err_curr = ((float)(in2 - ZEROV))/ZEROV;
  error_signal = 0.95*error_signal + 0.05*err_curr;

  out1 = params.output_offset_curr;
  out1 -= params.gain_ff*out0;
  
  if(params.c_integrator_on) {
    if(!pause_accumulator) {
       accumulator += params.gain_i*error_signal;
    }
    if(abs(accumulator) > ACCUMULATOR1_MAX and !pause_accumulator) {
      pause_accumulator = true;
      pause_time = micros();
    }
    if(pause_accumulator) {
      if(micros() - pause_time > INTEGRATOR_HOLD_TIME) {
        pause_accumulator = false;
        accumulator *= 0.9;
      }
    }
    out1 += accumulator;
  }
  else{
    accumulator = 0.0;
    pause_accumulator = false;
  }

  if(params.p_integrator_on) {
    if(!pause_accumulator)
      accumulator2 += params.gain_i2*accumulator;

    out0 -= accumulator2;
    //out0 -= (accumulator2 + 0.1*accumulator);
  }
  else {
    accumulator2 = 0.0;
  }
  if(params.c_gain_on) {
    out1 += params.gain_c*error_signal;
  }
  if(params.p_gain_on) {
    out0 -= params.gain_p*error_signal;
  }
  //out2 = ZEROV + (int) 10000*pause_accumulator;
  
  //out2 = ZEROV + accumulator2;

  if(abs(accumulator2) > ACCUMULATOR2_MAX) {
    // this could mean that we are out of lock... reset
    params.c_gain_on = false;
    params.p_gain_on = false;
    params.c_integrator_on = false;
    params.p_integrator_on = false;
    processParams();
    //accumulator = 0.0;
    //accumulator2 = 0.0;
    if (params.scan_state == STATE_AUTOSCAN){
      if (LPindexOffset < 100){
        LPindexOffset++;
      } else {
        LPindexOffset = 0;
      }
    }
    params.scan_state = STATE_AUTOSCAN;
  }
  // get the feedforward
  //AT THE TOP out1 -= params.gain_ff*out0;
  //out3 = ZEROV + accumulator;
  out2 = ZEROV + in2_offsetcorrection;
  analog.write(out0, out1, out2, out3, true);
}

/*
 * g - get params
 * w - write to eeprom
 * r - read from eeprom
 * i - return UNO_ID
 * s - set params
 */
void parseSerial() {
  char byte_read = Serial.read();

  switch(byte_read) {
    case 'g':
      // get params, send the entire struct in one go
      Serial.write((const uint8_t*)&params, sizeof(Params));
      break;
    case 'w':
      // write to EEPROM
      EEPROM_writeAnything(0, params);
      break;
    case 'r':
      EEPROM_readAnything(0, params);
      // EEPROM_readAnything(sizeof(params), logger);      
      break;
    case 'i':
      // return ID
      Serial.write(UNO_ID);
      break;
    case 's':
      // set params struct
      Serial.readBytes((char *) &params, sizeof(Params));
      processParams();
      break;
  }
}

template <class T> int EEPROM_writeAnything(int ee, const T& value)
{
    const byte* p = (const byte*)(const void*)&value;
    unsigned int i;
    for (i = 0; i < sizeof(value); i++)
          EEPROM.write(ee++, *p++);
    return i;
}

template <class T> int EEPROM_readAnything(int ee, T& value)
{
    byte* p = (byte*)(void*)&value;
    unsigned int i;
    for (i = 0; i < sizeof(value); i++)
          *p++ = EEPROM.read(ee++);
    return i;
}

float getPiezoLockPoint_fromMax (float in2_array[], float out0_array[]){
  // Assumed ramp down in2_array and negative discriminator slope on ramp down
  float pzLockPoint = 0.0;
  
  float in2_max = 0.0;
  int in2_max_index = 0;
  
  int in2_zc_index = 0;
  bool stayinloop = true;
  //float minmin = 32768.0 - (0.05/(5.0/32768.0));

  for (int i = 0; i<N_STEPS_DOWN; i++){
    if (in2_array[i]>in2_max){
      in2_max = in2_array[i];
      in2_max_index = i;
    }
  }
  int n = in2_max_index;
  while (stayinloop){
    if (n>4){
      float lave = 0.0;
      float counter = 0.0;
      //float uave = 0;
      for (int i = 0; i<5; i++){
          counter = counter + 1.0;
          lave = lave + in2_array[n-i];
          //uave = uave + in2_array[n+i];
      }
      lave = lave/counter;
      
      if (lave>zerov_float and in2_array[n+1]<=zerov_float){
        in2_zc_index = n;
        stayinloop = false;
      }
    }
    if (n==N_STEPS-1){
      stayinloop = false;
    }
    if (stayinloop){
      n++;
    }
  }
  //LPindexOffset = 1;
  if ((in2_max_index +LPindexOffset)>0 and (in2_max_index +LPindexOffset)<N_STEPS_DOWN){
    pzLockPoint = out0_array[in2_max_index+LPindexOffset];
  } 
  return pzLockPoint;
}

void runAutoScan(){
  if(ramp_direction) {     
    cycle_up += 1;
    ramp_offset += ramp_step*1;
    if(cycle_up == (int)(N_STEPS*(1/1))) 
    {
      cycle_up = 0;
      ramp_direction = false;
    }
  }
  else {
    in2_array[cycle_down] = in2;
    out0_array[cycle_down] = params.output_offset_pzt+ramp_offset;
    
    cycle_down += 1;
    ramp_offset -= ramp_step_down;
    
    if(cycle_down ==  N_STEPS_DOWN) {
      cycle_down = 0;
      ramp_direction = true;
      
      //find piezo lock point
      float lockpoint = getPiezoLockPoint_fromMax (in2_array, out0_array);
      if (lockpoint>0){
        out0 = lockpoint;//WATCH THIS VARIABLE 
        params.output_offset_pzt = lockpoint;
        processParams();// reset ramp parameters (like cycle_up, etc). 
        //delay(100);
        params.c_gain_on = true;
        params.p_gain_on = true;
        params.c_integrator_on = true;
        params.p_integrator_on = true;
        params.scan_state = STATE_NOT_SCANNING;
        accumulator = 0.0; // reset current integrators
        accumulator2 = 0.0;
      }
    }
  }
  if (params.scan_state == STATE_AUTOSCAN){
    out0 += ramp_offset; // out0 is reset in every loop to pz
  }
}

void runStdScan(){
  if(ramp_direction) {
    cycle_up += 1;
    ramp_offset += ramp_step*1;
    if(cycle_up >= (int)(N_STEPS*(0.5))) 
    {
      out3 = V2P5;
    } else {
      out3 = ZEROV;
    }
    if(cycle_up == (int)(N_STEPS*(1/1))) 
    {
      cycle_up = 0;
      ramp_direction = false;
    }
  }
  else {
    cycle_down += 1;
    ramp_offset -= ramp_step_down;
    if(cycle_down >= (int)(N_STEPS_DOWN*0.5)) 
    {
      out3 = ZEROV;
    } else {
      out3 = V2P5;
    }
    if(cycle_down ==  N_STEPS_DOWN) {
      cycle_down = 0;
      ramp_direction = true;
    }

  }
  out0 += ramp_offset;
}

