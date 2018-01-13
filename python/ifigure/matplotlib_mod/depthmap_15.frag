#version 150
in vec4 vColor;
in vec3 ClipDistance0;

uniform vec3  uClipLimit1;
uniform vec3  uClipLimit2;
uniform int  uUseClip;
uniform int  uHasHL;
uniform int  uUseSolidColor;
uniform vec4  uColor;

out vec4 FragData0;
out vec4 FragData1;

void main(){
     float bias = 0.001;
     if (uUseClip == 1){
     if (ClipDistance0[0] < uClipLimit1[0]-bias){
        discard;
     }
     if (ClipDistance0[1] < uClipLimit1[1]-bias){
        discard;
     }
     if (ClipDistance0[2] < uClipLimit1[2]-bias){
        discard;
     }
     if (ClipDistance0[0] > uClipLimit2[0]+bias){
        discard;
     }
     if (ClipDistance0[1] > uClipLimit2[1]+bias){
        discard;
     }
     if (ClipDistance0[2] > uClipLimit2[2]+bias){
        discard;
     }
     }

    // Not really needed, OpenGL does it anyway
    float moment1 = gl_FragCoord.z;
    float moment2 = gl_FragCoord.z * gl_FragCoord.z;
	
    // Adjusting moments (this is sort of bias per pixel) using partial derivative
    float dx = dFdx(gl_FragCoord.z);
    float dy = dFdy(gl_FragCoord.z);
    
    moment2 += 0.25*(dx*dx+dy*dy) ;
    moment1 = moment1*256*256;

    FragData0 = vec4((moment1 - 256*floor(moment1/256.))/255.,
                          floor(moment1/256)/255.,
                          moment1, moment1);
    FragData1 = vec4(gl_FragCoord.x, 1.0,
                          gl_FragCoord.z, moment2);
 			  
}