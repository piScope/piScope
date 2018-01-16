/*

   Vertex shader for OpenGL backend 

   This shader does
     1) take care of small offset in the normalized model coordinates.
        this avoid an ugly interference when contour is used with offset
     2) compute clip distance which allows clipping by axes3d 
        box
     3) small offset toward camera
     4) compute distance from a light source (shadow map)
     5) texture coordinate
   Need to do
     3) support Clipping at arbitray flat plane

*/
#version 150
in vec3 inVertex;
in vec4 inColor;
in float vertex_id;

out vec4 vColor;
out float vArrayID;
out vec3 vClipDistance;
out vec2 vAtlasData;
out float vAtlas;

uniform mat4 uWorldM;
uniform vec4 uWorldOffset;
uniform vec4 uViewOffset;
uniform mat3 uNormalM; // matrix_inverse_transpose of uProjM * (uViewM *(uWorldM
uniform mat4 uProjM;
uniform mat4 uViewM;
uniform vec4 uLightDir;

uniform mat4 uShadowM;
uniform float uShadowMaxZ;
uniform float uShadowMinZ;

uniform int uisImage;
uniform int uisAtlas;
uniform int uLineStyle;
uniform int uUseArrayID;
uniform vec3 uAtlasParam;

uniform int  uUseSolidColor;
uniform vec4  uColor;


void main() {
   if (uUseSolidColor == 1) {
      vColor = uColor;
   } else {
      vColor = inColor;
   }
   vec4 Vertex = vec4(inVertex, 1);
   gl_Position = uProjM * (uViewM *(uWorldM*Vertex) + uViewOffset);
   vClipDistance = vec3(uWorldM * Vertex);   
   if (uUseArrayID == 1){
       vArrayID = vertex_id;
   }
   if (uLineStyle != -1){
       vAtlas = vertex_id;
   }

}