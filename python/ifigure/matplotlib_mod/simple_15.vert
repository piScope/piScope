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
in vec3 inNormal;

in vec4 Vertex2;
in float vertex_id;
in vec2 inTexCoord;

out vec4 vColor0;
out vec3 ClipDistance0;
out vec3 normal;
out vec3 camera_dir;
out vec3 light_dir;
out vec3 LightDist;
out vec2 atlas_data;
out float atlas;
out float array_id;
out vec2 texCoord;

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

    if (uisImage == 1){
        texCoord = inTexCoord;
    }
    vec4 Vertex = vec4(inVertex, 1);
    vec4 pos1 = uProjM * (uViewM *(uWorldM*Vertex + uWorldOffset*10.)+
                          uViewOffset);
    vec4 pos2 = uProjM * (uViewM *(uWorldM*Vertex) + uViewOffset);
    gl_Position = vec4(pos2[0], pos2[1], pos1[2], pos2[3]);
    /* gl_PointSize = 30;    */
    /* gl_PointSize = 5;     */
    camera_dir = - (uViewM * uWorldM * Vertex).xyz;
    light_dir  = (uViewM * uWorldM * uLightDir).xyz;

    if (uisAtlas == 1){
       vec4 vertex2 = vec4(Vertex2);
       vertex2.w = 1;
       pos1 = uProjM * (uViewM *(uWorldM * vertex2 + uWorldOffset*10.)+
                          uViewOffset);
       pos2 = uProjM * (uViewM *(uWorldM * vertex2) + uViewOffset);
       atlas_data  = vec2(gl_Position.x/gl_Position.w - pos2[0]/pos2[3],
                          gl_Position.y/gl_Position.w - pos2[1]/pos2[3]);
       /*atlas_data  = vec2(Vertex.x, Vertex2.x);*/
       gl_Position = vec4(-1 + (vertex_id+0.5)/(uAtlasParam[0])*2, 0, 0, 1);

    } else {
       if (uUseSolidColor == 1) {
          vColor0 = uColor;
       } else {
          vColor0 = inColor;
       }
       normal = uNormalM * inNormal;
    
    
       ClipDistance0 = vec3(uWorldM * Vertex);
       LightDist = (uShadowM * Vertex).xyz/(uShadowM * Vertex).w;

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