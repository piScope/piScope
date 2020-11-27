/*
   a fragment shader written GLSL 1.5
   
   1) clip if the point is outside the box
   2) set color using interpolated color
   3) use marker texture, when uisMarker = 1
   4) lighting based on diffuse, ambient, and specular
   5) shadow map
   6) line style
   7) fixed artist color mode (color becomes a data along the path)

*/
#version 150
in vec4 gColor; 
in float gDist;
in float gArrayID;
in vec3 gClipDistance;
in float gAtlas;

out vec4 FragData0;
out vec4 FragData1;

uniform vec4 uViewOffset;
uniform vec4 uArtistID;
uniform vec4 uAmbient;
uniform vec3 uLightColor;
uniform float uLightPow;
uniform float uLightPowSpec;
uniform vec3  uClipLimit1;
uniform vec3  uClipLimit2;
uniform int  uisMarker;
uniform int  uUseClip;
uniform int  uHasHL;
uniform int  uAlphaTest;
uniform float  uAlphaLimit;
uniform vec4  uHLColor;
uniform sampler2D uMarkerTex;
uniform float nearZ;
uniform float farZ;
uniform int isFrust;


uniform int  uUseShadowMap;
uniform sampler2D uShadowTex;
uniform sampler2D uShadowTex2;
uniform sampler2D uRT0;
uniform sampler2D uRT1;
uniform int uisFinal;
uniform int uisClear;
uniform int uisSolid;
uniform vec2 uShadowTexSize;

uniform int uisImage;
uniform sampler2D uImageTex;

uniform int uisAtlas;
uniform vec3 uAtlasParam;
uniform ivec2 uSCSize;

uniform float uLineWidth;
uniform int uUseArrayID;
uniform int uLineStyle;
int dashed[32] = int[32](1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 0, 0, 0, 0, 0, 0,
                               0, 0, 0, 0, 0, 0, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1);
int dash_dot[32] = int[32](1, 1, 1, 1, 1, 1, 1, 1, 0, 0, 0, 0, 0, 1, 1, 1,
                                 1, 1, 1, 0, 0, 0, 0, 0, 1, 1, 1, 1, 1, 1, 1, 1);
int dotted[32] = int[32](0, 0, 0, 0, 0, 0, 1, 1, 1, 1, 1, 1, 1, 1, 0, 0,
                               0, 0, 0, 0, 0, 0, 1, 1, 1, 1, 1, 1, 1, 1, 0, 0);


void main() {
     /* just to make sure to write this variable */
     float bias = 0.001;
     /*
     if (uUseClip == 1){     
     if (gClipDistance[0] < uClipLimit1[0]-bias){
        discard;
     }
     if (gClipDistance[1] < uClipLimit1[1]-bias){
        discard;
     }
     if (gClipDistance[2] < uClipLimit1[2]-bias){
        discard;
     }
     if (gClipDistance[0] > uClipLimit2[0]+bias){
        discard;
     }
     if (gClipDistance[1] > uClipLimit2[1]+bias){
        discard;
     }
     if (gClipDistance[2] > uClipLimit2[2]+bias){
        discard;
     }
     }
     */
     // squre box clipping
     if ((uUseClip == 1) || (uUseClip == 3)){
        if (gClipDistance[0] < 0.0-bias){
           discard;
        }
        if (gClipDistance[1] < 0.0-bias){
           discard;
        }
        if (gClipDistance[2] < 0.0-bias){
           discard;
        }
        if (gClipDistance[0] > 1.0+bias){
           discard;
        }
        if (gClipDistance[1] > 1.0+bias){
           discard;
        }
        if (gClipDistance[2] > 1.0+bias){
           discard;
        }
     }

     // clip plane
     if ((uUseClip == 2) || (uUseClip == 3)){
        float dd_clip = ((gClipDistance[0]-0.5) * uClipLimit1[0] +
                      	 (gClipDistance[1]-0.5) * uClipLimit1[1] +
                 	 (gClipDistance[2]-0.5) * uClipLimit1[2] -
			 uClipLimit2[0]);
 	if ((uClipLimit2[1] > 0) && (dd_clip > bias)){
           discard;	
	}
 	if ((uClipLimit2[1] <= 0) && (dd_clip < bias)){	
           discard;	
	}
     }

     if (uLineStyle == 0){
         if (dashed[int(mod(gAtlas, 32))] == 0){
	     discard;
         }
     }
     if (uLineStyle == 1){     
         if (dash_dot[int(mod(gAtlas, 32))] == 0){
	     discard;
         }
     }
     if (uLineStyle == 2){     
         if (dotted[int(mod(gAtlas, 32))] == 0){
	     discard;
         }
     }

     gl_FragDepth = gl_FragCoord.z + uViewOffset.z*gl_FragCoord.w;
     
     FragData0 = gColor;

     if (abs(gDist) >  uLineWidth) {
         //FragData0.a = FragData0.a*(1. - (abs(gDist)-uLineWidth)/3);
         //FragData0 = FragData0*(1. - (abs(gDist)-uLineWidth)/3);	 
     }
     if (uHasHL == 1){
        if (((uUseArrayID == 1) && (gArrayID < 0)) || (uUseArrayID != 1)){
            /* alpha blend wiht uHLColor when it is highlighted. effective only
   	      during rot/pan */
            FragData0.a = uHLColor.a + (1-uHLColor.a)*FragData0.a;
            FragData0.rgb = uHLColor.a*uHLColor.rbg + (1-uHLColor.a)*FragData0.rgb;
	}
     }
     
     if (uisSolid == 1){
        FragData1 = uArtistID;
        if (uUseArrayID == 1){
	   float id = abs(gArrayID);
           FragData1.b = (id - 256*floor(id/256.))/255.;
	   FragData1.a = floor(id/256)/255.;
	}
	else
	{
           FragData1.b = -1/255.;
	   FragData1.a = 0;
	}

     	return;
     }

}
