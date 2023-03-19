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
in vec4 vColor0;
in vec3 ClipDistance0;
in vec3 normal;
in vec3 camera_dir;
in vec3 light_dir;
in vec3 LightDist;
in vec2 atlas_data;
in float atlas;
in float array_id;
in vec2 texCoord;

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

uniform int uUseArrayID;


uniform int uLineStyle;
int dashed[32] = int[32](1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 0, 0, 0, 0, 0, 0,
                               0, 0, 0, 0, 0, 0, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1);
int dash_dot[32] = int[32](1, 1, 1, 1, 1, 1, 1, 1, 0, 0, 0, 0, 0, 1, 1, 1,
                                 1, 1, 1, 0, 0, 0, 0, 0, 1, 1, 1, 1, 1, 1, 1, 1);
int dotted[32] = int[32](0, 0, 0, 0, 0, 0, 1, 1, 1, 1, 1, 1, 1, 1, 0, 0,
                               0, 0, 0, 0, 0, 0, 1, 1, 1, 1, 1, 1, 1, 1, 0, 0);

float chebyshevUpperBound(sampler2D depths, sampler2D depths2, vec2 uv, float compare){
    float moment1 = texture(depths, uv)[0];
    float moment2 = texture(depths2, uv)[0];
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
    float pixel = 0.0;
    for(int x=-2; x<=2; x++){
        for(int y=-2; y<=2; y++){
            vec2 off = vec2(x,y)/size;
	    pixel = texture(depths, uv + off)[0]/255. + texture(depths, uv + off)[1];
	    if (pixel > compare){
               result += 1;
	    }
        }
    }
    return result/25.0;
}
float SPOT(sampler2D depths, vec2 size, vec2 uv, float compare){
     if (texture(depths, uv)[0] > compare){
         return 1.;
     }
     return 0.;
}    

void main() {
     /* just to make sure to write this variable */
     gl_FragDepth = gl_FragCoord.z + uViewOffset.z*gl_FragCoord.w;
     
     if (uisClear == 1){
	 FragData0 = vec4(0,0,0,1);
         FragData1 = vec4(0,0,0,1);
	 return;
     }
     
     if (uisFinal == 1){
         vec4 accum = texture(uRT1, vec2(gl_FragCoord.xy/uSCSize.xy));
	 float r = accum.a;
         float count = texture(uRT0, vec2(gl_FragCoord.xy/uSCSize.xy)).g;
         float rrr = texture(uRT0, vec2(gl_FragCoord.xy/uSCSize.xy)).r;	 	 
         // Blend Func: GL_ONE_MINUS_SRC_ALPHA, GL_SRC_ALPHA
	 // sqrt in below is my adjustment
	 // here r is alpha_1*alpha_2*alpha_3.... (products of alphas of transparent layer)
         FragData0 = vec4(accum.rgb / clamp(rrr, 1e-4, 5e4),  1-sqrt(r));
	 //gl_FragData[0] = vec4(accum.rgb / clamp(rrr, 1e-4, 5e4),  1-sqrt(r));
	 //gl_FragData[0] = vec4(accum.rgb,  1);
	 /*
         if (uAlphaTest == 0){
    	    if (FragData0[3] < uAlphaLimit){
	       discard;
	    }
         }
	 */
	 return;
     }
     if (uisAtlas == 1){
         float data = length(vec2(atlas_data[0]*uAtlasParam[1], 
       	                          atlas_data[1]*uAtlasParam[2]));
         FragData0 = vec4(data/1000., 0, 0, 1);
         return;
     }
     float bias = 0.001;

     // squre box clipping
     if ((uUseClip == 1) || (uUseClip == 3)){
        if (ClipDistance0[0] < 0.0-bias){
           discard;
        }
        if (ClipDistance0[1] < 0.0-bias){
           discard;
        }
        if (ClipDistance0[2] < 0.0-bias){
           discard;
        }
        if (ClipDistance0[0] > 1.0+bias){
           discard;
        }
        if (ClipDistance0[1] > 1.0+bias){
           discard;
        }
        if (ClipDistance0[2] > 1.0+bias){
           discard;
        }
     }

     // clip plane
     float isOnCutPlane = 1.0;   // 1: regular mode 2:shilhouette (black)
     if ((uUseClip == 2) || (uUseClip == 3)){
        float dd_clip = ((ClipDistance0[0]-0.5) * uClipLimit1[0] +
                      	 (ClipDistance0[1]-0.5) * uClipLimit1[1] +
                 	 (ClipDistance0[2]-0.5) * uClipLimit1[2] -
			 uClipLimit2[0]);

        if (uClipLimit2[1] > 0.){
            if (dd_clip > bias){
               discard;
            }
            if (dd_clip > bias - bias*5){
	       // when point is very close to cut plane, suppress colors using
	       // quadraticall.
               isOnCutPlane = ((dd_clip - bias)/bias/5)*((dd_clip - bias)/bias/5);

            }
        } else {
            if (dd_clip < -bias){
                discard;
	    }
            if (dd_clip < - bias + bias*5){
	       // when point is very close to cut plane, suppress colors using
	       // quadraticall.
               isOnCutPlane = ((dd_clip + bias)/bias/5)*((dd_clip + bias)/bias/5);
            }
	}
     }

     vec3 n = normalize(normal);
     vec3 l = normalize(light_dir);
     vec3 c = normalize(camera_dir);
     vec4 light_color = vec4(uLightColor.xyz, 1);

     /* for debug do something crazy when uLightPow == 4*/
     if (uLightPow == 2.){
        n = vec3(0,0,1);
        l = vec3(0,0,1);
        c = vec3(0,0.1,0.9);	
     }
     
     float sh  = 1.0;
     if (uUseShadowMap == 1){
        float offset = 0.00005+0.00005*sqrt(1-dot(n,l)*dot(n,l));
        sh = PCF(uShadowTex, uShadowTexSize,
	                LightDist.xy, LightDist.z-offset)*1;
        /*
        sh = VSM(uShadowTex, uShadowTex2, uShadowTexSize,
	                 LightDist.xy, LightDist.z-0.0005);
        */
     }
     vec4 vColor = vColor0;

     if (uisImage == 1){
         vColor = texture(uImageTex, texCoord.st);
	 if (vColor[3] == 0){
	     discard;
	 }
	 vColor[3] = 1;

     }
     
     float isVisible = 0.0;
     if (dot(n,c)*dot(n,l) > 0.01){
	isVisible = 1.0;
     }
     float cT = clamp(abs(dot(n,l)) * isVisible, 0., 1)*sh;

     /* add fixed lights */
     float isVisible2 = 0.0;     
     vec3 l2 = normalize(vec3(0,-1,0.6));
     if (dot(n,c)*dot(n,l2) > -0.005){
	isVisible2 = 1.0;
     }
     float cT2 = clamp(abs(dot(n,l2)) * isVisible2, 0., 1)*0.5;
     vec3 l3 = normalize(vec3(-1, 1,0.6));
     isVisible2 = 0.0;     
     if (dot(n,c)*dot(n,l3) > -0.005){
	isVisible2 = 1.0;
     }
     cT2 = cT2 + clamp(abs(dot(n,l3)) * isVisible2, 0., 1)*0.5;
     cT2 = cT2 * uAmbient[0];

     vec3  sp_ray = reflect(-l, n);
     /*isVisible = clamp(sign(dot(sp_ray,c)), 0, 1)*isVisible;*/
     float cA = clamp(clamp(dot(sp_ray, c), 0,1 )*isVisible, 0., 1);
     cA = cA * sh;

     vec4 cAmbient = vColor * uAmbient;
     float LightPow = uLightPow;

     vec4 cDiff = vColor * vec4(LightPow*cT + cT2,
                                LightPow*cT + cT2,
				LightPow*cT + cT2, 1);
     vec4 cSpec = light_color * uLightPowSpec * pow(cA, 5)/2.;

     FragData0 = (cAmbient + cDiff + cSpec);
     FragData0.g = FragData0.g * isOnCutPlane;
     FragData0.b = FragData0.b * isOnCutPlane;     

     float aaa = FragData0.a * vColor[3];
     if (uHasHL == 1){
        if (((uUseArrayID == 1) && (array_id < 0)) || (uUseArrayID != 1)){
            /* alpha blend wiht uHLColor when it is highlighted. effective only
   	      during rot/pan */
            FragData0.a = uHLColor.a + (1-uHLColor.a)*FragData0.a;
            FragData0.rgb = uHLColor.a*uHLColor.rbg + (1-uHLColor.a)*FragData0.rgb;
	}
     }

     FragData0.a = vColor[3];
     vec4 color;     
     if (uisMarker == 1){
        color = texture(uMarkerTex, gl_PointCoord);
	if (color.a == 0){
	    discard;
	}
	FragData0 = color;

     }


/*     gl_FragDepth = gl_FragDepth +  uViewOffset.z/10*     
                    (1 + 3 * sqrt(1-dot(n,c)*dot(n,c)));*/

     /*gl_FragData[0] = vec4(cT, 0, 0, 1);*/
     /* debug for shadow map
     if (uUseShadowMap == 1){
        vec4 depth = texture(uShadowTex, LightDist.xy);
        if (LightDist.z > depth[0]){
            //inside shadow
            FragData0 = vec4(0, 0, 0, 1);
        }
	else
	{
	    FragData0 = vec4(1, 0, 0, 1);
	}
        FragData0 = vec4(LightDist.z, 0, 0, 1);	
     }
     FragData0 = vec4(cT, 0, 0, 1);	     
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
     
     if (uisSolid == 1){
        FragData1 = uArtistID;
        if (uUseArrayID == 1){
	   float id = abs(array_id);
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
     else
     {
        color = FragData0;

        // calculating weighting dependent on z
	// first we need z....
        float z_ndc = 0.0;
	float z_eye = 0.0;
        if (isFrust == 1){
            z_ndc = 2.0 * gl_FragCoord.z - 1.0;
            z_eye = 2.0 * nearZ * farZ/ (farZ + nearZ - z_ndc * (farZ - nearZ));
	}
	else
	{
            z_eye = gl_FragCoord.z * (farZ-nearZ) + nearZ;
        }
	// here scale is scaling factor
	// if scale is 1, z is 1 at nearZ, 1 at far 0
	float scale = 1;
	float z = clamp((z_eye - (nearZ + farZ)/2.0)/(nearZ- farZ)*scale+0.5, 0, 1);

        // (debug) gl_FragData[0].r = z;
	
        //float weight = max(min(1.0, max(max(color[0], color[1]), color[2])*color[0]), color[0])*clamp(0.03 / (1e-5 + pow(z * 500 / 200, 4.0)), 1e-2, 3e3);
        //float weight = vColor0[3]*clamp(0.03 / (1e-5 + pow(z*500./ 200, 4.0)), 1e-2, 3e3)
	;
	float weight =  clamp(3e3*pow(z, 3), 1e-2, 3e3)/3e3;
	//float weight =  1.;
        FragData1 = vec4(color.rgb * weight, vColor0[3]);
        FragData0.r = vColor0[3] * weight;

        //weight = clamp(0.03 / (1e-5 + pow(z*500./ 200, 4.0)), 1e-2, 3e3);
        //gl_FragData[0].r = pow(z, 3);
     }

}