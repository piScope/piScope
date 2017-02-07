#version 120
varying vec4 vColor;
varying vec3 ClipDistance0;

uniform mat4 uDepthMatrix;
uniform mat4 uWorldM;
uniform vec4 uWorldOffset;
uniform vec4 uViewOffset;
uniform mat4 uProjM;
uniform mat4 uViewM;

void main(){
    vec4 pos1 = uProjM * (uViewM *(uWorldM*gl_Vertex + uWorldOffset*10.)+
                          uViewOffset);
    vec4 pos2 = uProjM * (uViewM *(uWorldM*gl_Vertex) + uViewOffset);
    
    
    gl_Position = vec4(pos2[0], pos2[1], pos1[2], pos2[3]);
    vColor = gl_Color;
    ClipDistance0 = vec3(uWorldM * gl_Vertex);    
}