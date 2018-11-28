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
#version 120
attribute vec4 Vertex2;
attribute float vertex_id;

varying vec4 vColor0;
varying vec3 ClipDistance0;
varying vec3 normal;
varying vec3 camera_dir;
varying vec3 light_dir;
varying vec3 LightDist;
varying vec2 atlas_data;
varying float atlas;
varying float array_id;

uniform mat4 uWorldM;
uniform vec4 uWorldOffset;
uniform vec4 uViewOffset;

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

void main() {

    if (uisImage == 1){
        gl_TexCoord[0] = gl_MultiTexCoord0;
    }

    vec4 pos1 = uProjM * (uViewM *(uWorldM*gl_Vertex + uWorldOffset*10.)+
                          uViewOffset);
    vec4 pos2 = uProjM * (uViewM *(uWorldM*gl_Vertex) + uViewOffset);
    gl_Position = vec4(pos2[0], pos2[1], pos1[2], pos2[3]);    
    gl_PointSize = 6;
    
    if (uisAtlas == 1){
       vec4 vertex2 = vec4(Vertex2);
       vertex2.w = 1;
       pos1 = uProjM * (uViewM *(uWorldM * vertex2 + uWorldOffset*10.)+
                          uViewOffset);
       pos2 = uProjM * (uViewM *(uWorldM * vertex2) + uViewOffset);
       atlas_data  = vec2(gl_Position.x/gl_Position.w - pos2[0]/pos2[3],
                          gl_Position.y/gl_Position.w - pos2[1]/pos2[3]);
       /*atlas_data  = vec2(gl_Vertex.x, Vertex2.x);*/
       gl_Position = vec4(-1 + (vertex_id+0.5)/(uAtlasParam[0])*2, 0, 0, 1);

    } else {
       vColor0 = gl_Color;
       normal = gl_NormalMatrix * gl_Normal.xyz;
    
       //camera_dir = - (uViewM * uWorldM * vec4(gl_Position.xyz, 1)).xyz;
       camera_dir = - (uViewM * uWorldM * vec4(gl_Vertex.xyz, 1)).xyz;
       light_dir  = (uViewM * uWorldM * uLightDir).xyz;
       //light_dir  = gl_NormalMatrix *  uLightDir.xyz;
    
       ClipDistance0 = vec3(uWorldM * gl_Vertex);
       LightDist = (uShadowM * gl_Vertex).xyz/(uShadowM * gl_Vertex).w;

       LightDist[0] = (LightDist[0]+1.0)/2.0;
       LightDist[1] = (LightDist[1]+1.0)/2.0;
       LightDist[2] = (LightDist[2]+1.0)/2.0;
      /*LightDist = (LightDist - uShadowMinZ)/(uShadowMaxZ - uShadowMinZ);*/
   }
   if (uLineStyle != -1){
       atlas = vertex_id;
   }
   if (uUseArrayID == 1){
       array_id = vertex_id;
   }

}