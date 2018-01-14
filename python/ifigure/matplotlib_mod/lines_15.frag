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

void main() {
     /* just to make sure to write this variable */
     gl_FragDepth = gl_FragCoord.z + uViewOffset.z*gl_FragCoord.w;
     
     FragData0 = gColor;

     if (abs(gDist) >  uLineWidth) {
          FragData0.a = FragData0.a*(1. - (abs(gDist)-uLineWidth)/3);
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
