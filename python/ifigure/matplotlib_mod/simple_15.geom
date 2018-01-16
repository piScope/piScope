// Geometry Shader
#version 150
layout(lines) in;
layout(triangle_strip, max_vertices = 4) out;

//in vec4 vColor0[];
//in vec3 normal[];
//in float atlas[];
in vec4 v_vColor0[];
in vec3 v_ClipDistance0[];
in vec3 v_normal[];
in vec3 v_camera_dir[];
in vec3 v_light_dir[];
in vec3 v_LightDist[];
in vec2 v_atlas_data[];
in float v_atlas[];
in float v_array_id[];

out vec2 texCoord;
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

void main()
{
    gl_Position = gl_in[0].gl_Position + vec4(-0.1, 0.0, 0.0, 0.0);
    EmitVertex();
    gl_Position = gl_in[0].gl_Position;
    EmitVertex();
    gl_Position = gl_in[1].gl_Position;
    EmitVertex();
    gl_Position = gl_in[1].gl_Position + vec4(0.1, 0.0, 0.0, 0.0);
    EmitVertex();

    EndPrimitive();
}
