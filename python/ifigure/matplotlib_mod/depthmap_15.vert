#version 150
in vec4 inVertex;
in vec4 inColor;

out vec4 vColor;
out vec3 ClipDistance0;

uniform mat4 uDepthMatrix;
uniform mat4 uWorldM;
uniform vec4 uWorldOffset;
uniform vec4 uViewOffset;
uniform mat4 uProjM;
uniform mat4 uViewM;

void main(){
    vec4 pos1 = uProjM * (uViewM *(uWorldM * inVertex + uWorldOffset*10.)+
                          uViewOffset);
    vec4 pos2 = uProjM * (uViewM *(uWorldM * inVertex) + uViewOffset);
    
    
    gl_Position = vec4(pos2[0], pos2[1], pos1[2], pos2[3]);
    vColor = inColor;
    ClipDistance0 = vec3(uWorldM * inVertex);    
}