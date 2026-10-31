#include "eye_animation.h"
#include <math.h>
#include <string.h>
static float clamp(float x,float a,float b){return x<a?a:x>b?b:x;}
static const char *const performance_patterns[][8]={
 {"00000000","00000000","01111110","01111110","00111100","00000000","00000000","00000000"},
 {"00000000","01000010","00100100","00011000","00100100","01000010","00000000","00000000"},
 {"01100110","11111111","11111111","11111111","01111110","00111100","00011000","00000000"},
 {"00011000","00011000","00111100","11111111","11111111","00111100","00011000","00011000"},
 {"00000001","00000011","00000110","00001100","11011000","01110000","00100000","00000000"},
 {"00000000","00111100","01100110","11000011","11011011","11000011","01111110","00000000"},
 {"00000000","00000000","00011000","00111100","00111100","00011000","00000000","00000000"}
};
static void render_performance(uint8_t out[EYE_BYTES],eye_mode_t mode){
 int pattern=mode==EYE_PUPIL_LEFT||mode==EYE_PUPIL_RIGHT?EYE_PUPIL_LEFT-EYE_CALM:mode-EYE_CALM;
 int shift=mode==EYE_PUPIL_LEFT?-2:mode==EYE_PUPIL_RIGHT?2:0;
 for(int y=0;y<EYE_HEIGHT;y++)for(int x=0;x<EYE_WIDTH;x++){
  int px=x/16-shift;
  if(px>=0 && px<8 && performance_patterns[pattern][y/8][px]=='1')
   out[x+(y/8)*EYE_WIDTH]|=(uint8_t)(1u<<(y%8));
 }
}
void eye_render(uint8_t out[EYE_BYTES],unsigned side,eye_mode_t mode,uint32_t now,uint32_t elapsed){
 memset(out,0,EYE_BYTES);
 if(mode>=EYE_CALM && mode<EYE_MODE_COUNT){render_performance(out,mode);return;}
 float t=now*.001f, cx=64+10*sinf(t*.7f), cy=32, rx=29, ry=23;
 float open=clamp((float)(mode==EYE_OPEN?elapsed:now)/1100,0,1);
 if(mode==EYE_LISTEN){cx=64;ry=26;}
 if(mode==EYE_THINK){cx=64+15*sinf(t*1.4f);cy=26;ry=17;}
 if(mode==EYE_SPEAK){cx=64+7*sinf(t*2);ry=22+3*sinf(t*8);}
 if(mode==EYE_SURPRISE){rx=32;ry=29;cx=64;}
 if(mode==EYE_SLEEP)open*=.08f;
 unsigned blink=now%4300;
 if(blink>4000 && mode!=EYE_SLEEP)open*=fabsf((float)blink-4150)/150;
 if(mode==EYE_WINK && side==0 && elapsed<600)open*=fabsf((float)elapsed-300)/300;
 ry=fmaxf(1,ry*open);
 for(int y=0;y<EYE_HEIGHT;y++)for(int x=0;x<EYE_WIDTH;x++){
  float dx=(x-cx)/rx,dy=(y-cy)/ry;
  int on=dx*dx+dy*dy<=1;
  if(mode==EYE_HAPPY && ry>3)on=on && y<cy-ry*.1f && y>cy-ry*.55f-6*dx*dx;
  if(on)out[x+(y/8)*EYE_WIDTH]|=(uint8_t)(1u<<(y%8));
 }
}
