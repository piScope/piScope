/*
   a fragment shader written GLSL 1.5 (OpenGL 3.2)
   
   1) clip if the point is outside the box
   2) set color using interpolated color
   3) use marker texture, when uisMarker = 1
   4) lighting based on diffuse, ambient, and specular

   Todo.
   1) shadow map
   2) line style
*/
#version 150
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
uniform sampler2D uShadowTex;
uniform sampler2D uShadowTex2;
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

float chebyshevUpperBound(sampler2D depths, sampler2D depths2, vec2 uv, float compare){
    float moment1 = texture2D(depths, uv)[0];
    float moment2 = texture2D(depths2, uv)[0];
    // Surface is fully lit. as the current fragment is before the light occluder
    if (compare <= moment1)
	return 1.0 ;
    // The fragment is either in shadow or penumbra. We now use chebyshev's upperBound to check
    // How likely this pixel is to be lit (p_max)
    float variance = moment2 - (moment1 * moment1);
    variance = max(variance, 0.0000002);
    
    float d = compare - moment1;
    float p_max = variance / (variance + d*d);
    return p_max;
}

float VSM(sampler2D depths, sampler2D depths2, vec2 size, vec2 uv, float compare){
    float result = 0.0;
    for(int x=-2; x<=2; x++){
        for(int y=-2; y<=2; y++){
            vec2 off = vec2(x,y)/size;
            result += chebyshevUpperBound(depths, depths2,  uv, compare);
        }
    }
    return result/25;
}

float PCF(sampler2D depths, vec2 size, vec2 uv, float compare){
    float result = 0.0;
    for(int x=-2; x<=2; x++){
        for(int y=-2; y<=2; y++){
            vec2 off = vec2(x,y)/size;
	    if (texture2D(depths, uv + off)[0] > compare){
               result += 1;
	    }
        }
    }
    return result/25.0;
}
float SPOT(sampler2D depths, vec2 size, vec2 uv, float compare){
     if (texture2D(depths, uv)[0] > compare){
         return 1.;
     }
     return 0.;
}    

void main() {
     gl_FragDepth = gl_FragCoord.z; /* just to make sure to write this variable */
     
     if (uisAtlas == 1){
         float data = length(vec2(atlas_data[0]*uAtlasParam[1], 
       	                          atlas_data[1]*uAtlasParam[2]));
         gl_FragData[0] = vec4(data, 0, 0, 1); 
/*         gl_FragData[0] = vec4(atlas_data[1], 0, 0, 1);  */
/*         gl_FragData[0] = vec4(gl_FragCoord.x, 0, 0, 1);	 */
         return;
     }
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
     vec3 n = normalize(normal);
     vec3 l = normalize(light_dir);
     vec3 c = normalize(camera_dir);
     vec4 light_color = vec4(uLightColor.xyz, 1);
     
     float sh  = 1.0;
     if (uUseShadowMap == 1){
        float offset = 0.005+0.005*sqrt(1-dot(n,l)*dot(n,l));
        sh = PCF(uShadowTex, uShadowTexSize,
	                LightDist.xy, LightDist.z-offset)*1;
        /*
        sh = VSM(uShadowTex, uShadowTex2, uShadowTexSize,
	                 LightDist.xy, LightDist.z-0.005);
        */
     }
     vec4 vColor = vColor0;
     if (uisImage == 1){
         vColor = texture2D(uImageTex, gl_TexCoord[0].st);
	 if (vColor[3] == 0){
	     discard;
	 }
	 vColor[3] = 1;

     }
     
     float isVisible = 0.0;
     if (dot(n,c)*dot(n,l) > 0.01){
	isVisible = 1.0;
     }
     /*sh = sh * isVisible; */
     /*
     isVisible = clamp(sign(dot(n,c)*dot(n,l)), 0., 1);     
     float cT = (clamp(abs(dot(n,l)) * isVisible, 0.2, 1)-0.2)/0.8;
     */
     float cT = clamp(abs(dot(n,l)) * isVisible, 0., 1)*sh;
     
     vec3  sp_ray = reflect(-l, n);
     /*isVisible = clamp(sign(dot(sp_ray,c)), 0, 1)*isVisible;*/
     float cA = clamp(clamp(dot(sp_ray, c), 0,1 )*isVisible, 0., 1);
     cA = cA * sh;

     vec4 cAmbient = vColor * uAmbient;

     vec4 cDiff = vColor * light_color * vec4(uLightPow*cT,
                       uLightPow*cT, uLightPow*cT, 1);
     //vec4 cDiff = vColor * light_color * vec4(cT, cT, cT, 1);
     vec4 cSpec = light_color * uLightPowSpec * pow(cA, 5)/2.;

     gl_FragData[0] = cAmbient + cDiff + cSpec;
     float aaa = gl_FragData[0].a * vColor[3];
     if (uHasHL == 1){
         /* make it darker when it is highlighted. effective only
	    during rot/pan */
         gl_FragData[0] = gl_FragData[0]/4.;
     }
     gl_FragData[0].a = aaa;   
     
     gl_FragData[1] = uArtistID;
     if (uisMarker == 1){
        vec4 color = texture2D(uMarkerTex, gl_PointCoord);
        gl_FragData[0] = vec4(1, 1, 1, 1);
	if (gl_PointCoord[0] > 0.5){
            gl_FragData[0] = vec4(0,1,1,1);
	}
        gl_FragData[0] = color; 
     }


     gl_FragDepth = gl_FragCoord.z + uViewOffset.z*gl_FragCoord.w;
/*     gl_FragDepth = gl_FragDepth +  uViewOffset.z/10*     
                    (1 + 3 * sqrt(1-dot(n,c)*dot(n,c)));*/

     /*gl_FragData[0] = vec4(cT, 0, 0, 1);*/
     /* debug for shadow map
     if (uUseShadowMap == 1){
        vec4 depth = texture2D(uShadowTex, LightDist.xy);
        if (LightDist.z > depth[0]){
            //inside shadow
            gl_FragData[0] = vec4(0, 0, 0, 1);
        }
	else
	{
	     gl_FragData[0] = vec4(1, 0, 0, 1);
	}
        gl_FragData[0] = vec4(LightDist.z, 0, 0, 1);	
     }
     gl_FragData[0] = vec4(cT, 0, 0, 1);	     
     */

     if (uLineStyle == 0){     
         if (dashed[int(mod(atlas, 32))] == 0){
	     discard;
         }
     }
     if (uLineStyle == 1){     
         if (dash_dot[int(mod(atlas, 32))] == 0){
	     discard;
         }
     }
     if (uLineStyle == 2){     
         if (dotted[int(mod(atlas, 32))] == 0){
	     discard;
         }
     }


/*         gl_FragData[0] = vec4(atlas, 0, 0, 1);	 */

}
