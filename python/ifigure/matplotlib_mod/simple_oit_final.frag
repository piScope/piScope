/*
   a fragment shader written GLSL 1.2
     -- limitation in 1.2 --
       * geometry shader is not available
          ** parametric curve needs to be expanded on CPU?
       * drawarraysinstanced does not exist?
   
   1) clip if the point is outside the box
   2) set color using interpolated color
   3) use marker texture, when uisMarker = 1
   4) lighting based on diffuse, ambient, and specular

   Todo.
   1) shadow map
   2) line style
*/
#version 120
varying vec4 vColor0;
varying vec3 ClipDistance0;
varying vec3 normal;
varying vec3 camera_dir;
varying vec3 light_dir;
varying vec3 LightDist;
varying vec2 atlas_data;
varying float atlas;

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
uniform sampler2D uMarkerTex;

uniform int  uUseShadowMap;
uniform sampler2D uRT0;
uniform sampler2D uRT1;
uniform vec2 uShadowTexSize;

uniform int uisImage;
uniform sampler2D uImageTex;

uniform int uisAtlas;
uniform vec3 uAtlasParam;

uniform int uLineStyle;
int dashed[32] = int[32](1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 0, 0, 0, 0, 0, 0,
                               0, 0, 0, 0, 0, 0, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1);
int dash_dot[32] = int[32](1, 1, 1, 1, 1, 1, 1, 1, 0, 0, 0, 0, 0, 1, 1, 1,
                                 1, 1, 1, 0, 0, 0, 0, 0, 1, 1, 1, 1, 1, 1, 1, 1);
int dotted[32] = int[32](0, 0, 0, 0, 0, 0, 1, 1, 1, 1, 1, 1, 1, 1, 0, 0,
                               0, 0, 0, 0, 0, 0, 1, 1, 1, 1, 1, 1, 1, 1, 0, 0);
			       
void main() {
     gl_FragDepth = gl_FragCoord.z; /* just to make sure to write this variable */
     
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
     vec4 accum = texture2D(uRT0, gl_FragCoord.xy, 0);
     float reveal = texture2D(uRT1, gl_FragCoord.xy, 0).r;
 
     // Blend Func: GL_ONE_MINUS_SRC_ALPHA, GL_SRC_ALPHA
     gl_FragData[0] = vec4(accum.rgb / max(accum.a, 1e-5), reveal);
     gl_FragData[1] = uArtistID;     

}
