/*
   Geometry Shader for anti-aliased lines.

   Input : a line segment.
   Output: two triangles (strip).
           distance from the center of line.
	   pass through the length along the line (atlas)
*/

#version 150
layout(triangles) in;
layout(triangle_strip, max_vertices = 10) out;

in  vec4  vColor[];
in  float vArrayID[];
in  vec3  vClipDistance[];
in  float vAtlas[];

out vec4  gColor;
out float gDist;
out float gArrayID;
out vec3  gClipDistance;
out float gAtlas;

uniform float uLineWidth;
uniform ivec2 uSCSize;
void main()
{
    int extra_w = 3;
    
    vec4 n = vec4( (gl_in[1].gl_Position[1]-gl_in[0].gl_Position[1])*uSCSize.y,
                  (-gl_in[1].gl_Position[0]+gl_in[0].gl_Position[0])*uSCSize.x,
		   0, 0);

    float len = sqrt(pow(n.x, 2) + pow(n.y, 2));
    n = n/len*(uLineWidth+0.7);
    n.xy = n.xy/uSCSize.xy;

    vec4 n0 = n*gl_in[0].gl_Position.w;
    vec4 n1 = n*gl_in[1].gl_Position.w;
    
    gColor = vColor[0];
    gArrayID = vArrayID[0];
    gAtlas = vAtlas[0];
    gClipDistance = vClipDistance[0];
    
    gDist  = -uLineWidth-extra_w;
    gl_Position = gl_in[0].gl_Position + n0;
    EmitVertex();
    
    gl_Position = gl_in[0].gl_Position - n0;
    gDist  = uLineWidth+extra_w;    
    EmitVertex();

    gColor = vColor[1];
    gArrayID = vArrayID[1];
    gClipDistance = vClipDistance[1];
    gAtlas = vAtlas[1];    
    
    gl_Position = gl_in[1].gl_Position + n1;
    gDist  = -uLineWidth-extra_w;        
    EmitVertex();
    
    gDist  = uLineWidth+extra_w;            
    gl_Position = gl_in[1].gl_Position - n1;

    EmitVertex();
    EmitVertex();    

    n = vec4( (gl_in[2].gl_Position[1]-gl_in[1].gl_Position[1])*uSCSize.y,
                  (-gl_in[2].gl_Position[0]+gl_in[1].gl_Position[0])*uSCSize.x,
		   0, 0);

    len = sqrt(pow(n.x, 2) + pow(n.y, 2));
    n = n/len*(uLineWidth+0.7);
    n.xy = n.xy/uSCSize.xy;

    n0 = n*gl_in[1].gl_Position.w;
    n1 = n*gl_in[2].gl_Position.w;
    
    gColor = vColor[1];
    gArrayID = vArrayID[1];
    gAtlas = vAtlas[1];
    gClipDistance = vClipDistance[1];

    
    gDist  = -uLineWidth-extra_w;
    gl_Position = gl_in[1].gl_Position + n0;
    EmitVertex();
    EmitVertex();    
    
    gl_Position = gl_in[1].gl_Position - n0;
    gDist  = uLineWidth+extra_w;    
    EmitVertex();

    gColor = vColor[2];
    gArrayID = vArrayID[2];
    gClipDistance = vClipDistance[2];
    gAtlas = vAtlas[2];    
    
    gl_Position = gl_in[2].gl_Position + n1;
    gDist  = -uLineWidth-extra_w;        
    EmitVertex();
    
    gDist  = uLineWidth+extra_w;            
    gl_Position = gl_in[2].gl_Position - n1;

    EmitVertex();

    EndPrimitive();

}
