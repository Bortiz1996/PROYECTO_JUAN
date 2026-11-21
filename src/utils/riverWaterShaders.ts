import * as THREE from "three";

export function createParticleTexture(): THREE.CanvasTexture {
  const size = 32;
  const c = document.createElement("canvas");
  c.width = size;
  c.height = size;
  const ctx = c.getContext("2d")!;
  const grad = ctx.createRadialGradient(
    size / 2,
    size / 2,
    0,
    size / 2,
    size / 2,
    size / 2
  );
  grad.addColorStop(0, "rgba(235, 252, 255, 0.85)");
  grad.addColorStop(0.45, "rgba(180, 238, 245, 0.35)");
  grad.addColorStop(1, "rgba(120, 210, 225, 0.0)");
  ctx.fillStyle = grad;
  ctx.fillRect(0, 0, size, size);
  const tex = new THREE.CanvasTexture(c);
  tex.colorSpace = THREE.SRGBColorSpace;
  return tex;
}

export function createWaterNormalMap(size = 256): THREE.DataTexture {
  const heightField = new Float32Array(size * size);
  const twoPi = Math.PI * 2;
  for (let y = 0; y < size; y++) {
    const v = y / size;
    for (let x = 0; x < size; x++) {
      const u = x / size;
      const h =
        Math.sin(twoPi * (u * 2 + v * 1) + 0.4) * 0.36 +
        Math.cos(twoPi * (u * 3 - v * 2) + 1.1) * 0.24 +
        Math.sin(twoPi * (u * 5 + v * 3) + 2.3) * 0.16 +
        Math.cos(twoPi * (u * 7 - v * 5) + 0.7) * 0.11 +
        Math.sin(twoPi * (u * 11 + v * 8) + 1.9) * 0.05;
      heightField[y * size + x] = h;
    }
  }

  const data = new Uint8Array(size * size * 4);
  const strength = 0.85;
  for (let y = 0; y < size; y++) {
    const yPrev = (y - 1 + size) % size;
    const yNext = (y + 1) % size;
    for (let x = 0; x < size; x++) {
      const xPrev = (x - 1 + size) % size;
      const xNext = (x + 1) % size;

      const dX =
        (heightField[y * size + xNext] - heightField[y * size + xPrev]) *
        strength;
      const dY =
        (heightField[yNext * size + x] - heightField[yPrev * size + x]) *
        strength;

      const len = Math.hypot(-dX, -dY, 1.0);
      const nx = -dX / len;
      const ny = -dY / len;
      const nz = 1.0 / len;

      const idx = (y * size + x) * 4;
      data[idx] = Math.round((nx * 0.5 + 0.5) * 255);
      data[idx + 1] = Math.round((ny * 0.5 + 0.5) * 255);
      data[idx + 2] = Math.round((nz * 0.5 + 0.5) * 255);
      data[idx + 3] = 255;
    }
  }

  const normalMap = new THREE.DataTexture(
    data,
    size,
    size,
    THREE.RGBAFormat,
    THREE.UnsignedByteType
  );
  normalMap.wrapS = THREE.RepeatWrapping;
  normalMap.wrapT = THREE.RepeatWrapping;
  normalMap.colorSpace = THREE.NoColorSpace;
  normalMap.generateMipmaps = true;
  normalMap.minFilter = THREE.LinearMipmapLinearFilter;
  normalMap.magFilter = THREE.LinearFilter;
  normalMap.needsUpdate = true;
  return normalMap;
}

export const WATER_VERTEX_SHADER = /* glsl */ `
  varying vec2 vUv;
  varying vec2 vScenePos;
  void main() {
    vUv = uv;
    vec4 worldPos = modelMatrix * vec4(position, 1.0);
    vScenePos = worldPos.xy;
    gl_Position = projectionMatrix * viewMatrix * worldPos;
  }
`;

export const WATER_BACK_FRAGMENT_SHADER = /* glsl */ `
  precision highp float;
  uniform float uTime;
  uniform float uSurfaceSceneY;
  uniform float uWindFactor;
  uniform float uNight;
  uniform float uStorm;
  uniform float uRain;
  uniform sampler2D uNormalMap;
  varying vec2 vUv;
  varying vec2 vScenePos;

  float hash(vec2 p) {
    return fract(sin(dot(p, vec2(127.1, 311.7))) * 43758.5453123);
  }

  float noise(vec2 p) {
    vec2 i = floor(p);
    vec2 f = fract(p);
    vec2 u = f * f * (3.0 - 2.0 * f);
    return mix(
      mix(hash(i + vec2(0.0, 0.0)), hash(i + vec2(1.0, 0.0)), u.x),
      mix(hash(i + vec2(0.0, 1.0)), hash(i + vec2(1.0, 1.0)), u.x),
      u.y
    );
  }

  // Domain-warped slow flow normal so there is zero repetitive tile pattern
  vec3 sampleFlowNormal(vec2 scenePos, float t, float wind) {
    float flowSpeed = 0.013 + wind * 0.008;
    vec2 warp = vec2(
      noise(scenePos * 0.011 + vec2(-t * 0.08, 0.5)),
      noise(scenePos * 0.013 + vec2(-t * 0.06, 3.1))
    ) * 0.12;
    vec2 uv1 = scenePos * vec2(0.0038, 0.0075) - vec2(t * flowSpeed, t * 0.002) + warp;
    vec2 uv2 = scenePos * vec2(0.0061, 0.0108) - vec2(t * (flowSpeed * 1.37), -t * 0.003) - warp * 0.7;
    vec3 n1 = texture2D(uNormalMap, uv1).xyz * 2.0 - 1.0;
    vec3 n2 = texture2D(uNormalMap, uv2).xyz * 2.0 - 1.0;
    return normalize(vec3(n1.xy * 0.34 + n2.xy * 0.24, 1.0));
  }

  float causticPattern(vec2 p, float t) {
    vec2 p1 = p * vec2(0.026, 0.042) + vec2(-t * 0.09, t * 0.05);
    vec2 p2 = p * vec2(0.034, 0.023) + vec2(t * 0.07, -t * 0.08);
    float w1 = sin(p1.x * 2.6 + sin(p1.y * 2.2 + t * 0.55) * 0.9);
    float w2 = sin(p2.y * 2.7 + sin(p2.x * 2.1 - t * 0.45) * 0.85);
    float ridge = 1.0 - abs(w1 + w2 * 0.7) * 0.5;
    return pow(clamp(ridge, 0.0, 1.0), 4.8);
  }

  // Organic mirrored foliage canopy height profile matching the ecological banks
  float shorelineCanopyMask(float x, float depth, vec2 perturb) {
    float sx = x + perturb.x * 16.0;
    float canopyDepth =
      36.0 +
      sin(sx * 0.021 + 0.6) * 18.0 +
      cos(sx * 0.053 - 1.2) * 12.0 +
      sin(sx * 0.097 + 2.4) * 7.0;
    // Left and right riverbank trees extend deeper reflections
    float sideBoost = smoothstep(45.0, 155.0, abs(sx)) * 22.0;
    float maxReflDepth = canopyDepth + sideBoost;
    float distortedDepth = depth + perturb.y * 7.0;
    return 1.0 - smoothstep(maxReflDepth * 0.45, maxReflDepth, distortedDepth);
  }

  void main() {
    float x = vScenePos.x;
    float y = vScenePos.y;

    vec3 flowNormal = sampleFlowNormal(vScenePos, uTime, uWindFactor);

    // Nearly glass-calm river surface: non-harmonic micro-ripples (~0.18 - 0.32 px)
    float waveSpeed = 0.28 + uWindFactor * 0.20;
    float waveAmp = 0.16 + uWindFactor * 0.14;
    float w1 = sin(x * 0.031 - uTime * waveSpeed) * waveAmp;
    float w2 = sin(x * 0.073 + uTime * (waveSpeed * 0.61) + 1.4) * (waveAmp * 0.45);
    float w3 = cos(x * 0.119 - uTime * (waveSpeed * 0.37) + 2.8) * (waveAmp * 0.25);
    float surfaceY = uSurfaceSceneY + w1 + w2 + w3 + flowNormal.y * 0.08;

    float depth = surfaceY - y;
    if (depth < -0.6) discard;
    float surfaceEdge = smoothstep(-0.5, 1.4, depth);

    float waterSpan = max(40.0, surfaceY - (-250.0));
    float normDepth = clamp(depth / waterSpan, 0.0, 1.0);

    vec3 shallowDay = mix(vec3(0.16, 0.56, 0.60), vec3(0.20, 0.48, 0.52), uStorm * 0.75 + uRain * 0.35);
    vec3 midDay     = mix(vec3(0.06, 0.39, 0.46), vec3(0.09, 0.31, 0.38), uStorm * 0.8 + uRain * 0.3);
    vec3 deepDay    = mix(vec3(0.03, 0.19, 0.25), vec3(0.04, 0.15, 0.21), uStorm * 0.8);

    vec3 shallowNight = vec3(0.07, 0.32, 0.39);
    vec3 midNight     = vec3(0.03, 0.19, 0.27);
    vec3 deepNight    = vec3(0.02, 0.09, 0.15);

    vec3 cShallow = mix(shallowDay, shallowNight, uNight);
    vec3 cMid     = mix(midDay, midNight, uNight);
    vec3 cDeep    = mix(deepDay, deepNight, uNight);

    vec3 baseColor = normDepth < 0.45
      ? mix(cShallow, cMid, normDepth / 0.45)
      : mix(cMid, cDeep, (normDepth - 0.45) / 0.55);

    // Organic surface reflection of sky & shoreline trees/foliage
    float reflFalloff = exp(-depth * 0.017) * (1.0 - uStorm * 0.45);
    float foliageMask = shorelineCanopyMask(x, depth, flowNormal.xy);
    vec3 skyReflDay = mix(vec3(0.62, 0.84, 0.90), vec3(0.55, 0.68, 0.73), uRain * 0.75 + uStorm * 0.4);
    vec3 skyReflNight = vec3(0.15, 0.28, 0.38);
    vec3 skyRefl = mix(skyReflDay, skyReflNight, uNight);

    float leafVar = noise(vec2(x * 0.05 + flowNormal.x * 3.0, depth * 0.04 - uTime * 0.05));
    vec3 foliageReflDay = mix(vec3(0.11, 0.31, 0.21), vec3(0.19, 0.42, 0.24), leafVar);
    vec3 foliageReflNight = mix(vec3(0.04, 0.12, 0.10), vec3(0.07, 0.17, 0.13), leafVar);
    vec3 foliageRefl = mix(foliageReflDay, foliageReflNight, uNight);

    vec3 envReflection = mix(skyRefl, foliageRefl, foliageMask * 0.82);
    float grazing = mix(0.24, 0.42, exp(-depth * 0.06));
    baseColor = mix(baseColor, envReflection, reflFalloff * grazing);

    // Soft filtered sunbeams & gentle underwater caustics
    float rayAngleCoord = (x + 170.0) * 0.82 - depth * 0.36 + flowNormal.x * 7.0;
    float ray1 = sin(rayAngleCoord * 0.041 + uTime * 0.16 + noise(vec2(x * 0.018, uTime * 0.07)) * 1.1);
    float ray2 = sin(rayAngleCoord * 0.079 - uTime * 0.11 + 1.7);
    float godRay = pow(clamp(ray1 * 0.55 + ray2 * 0.45, 0.0, 1.0), 2.6);
    float rayAtten = exp(-normDepth * 2.2) * (1.0 - uStorm * 0.75) * (1.0 - uRain * 0.45);
    vec3 rayColor = mix(vec3(0.76, 0.95, 0.94), vec3(0.42, 0.68, 0.84), uNight);
    baseColor += rayColor * godRay * rayAtten * mix(0.16, 0.06, uNight);

    vec2 causticCoord = vec2(x + depth * 0.15, y * 1.3) + flowNormal.xy * 8.0;
    float caust = causticPattern(causticCoord, uTime * (0.45 + uWindFactor * 0.2));
    float caustFade = exp(-normDepth * 2.5) * (1.0 - uStorm * 0.7);
    vec3 caustColor = mix(vec3(0.58, 0.90, 0.89), vec3(0.32, 0.62, 0.76), uNight);
    baseColor += caustColor * caust * caustFade * mix(0.18, 0.08, uNight);

    // Subtle natural organic river sediment & tea-tint
    float turbidity = noise(vec2(x * 0.022 - uTime * 0.11, y * 0.028 + uTime * 0.03));
    baseColor += (turbidity - 0.5) * vec3(0.025, 0.045, 0.032) * (0.5 + 0.5 * normDepth);

    // Soft silky meniscus highlight along the waterline
    float meniscus = exp(-depth * 0.34);
    float shimmer = pow(max(0.0, sin(x * 0.085 - uTime * 0.85 + flowNormal.x * 1.4)), 5.0);
    vec3 rimColor = mix(vec3(0.84, 0.96, 0.96), vec3(0.48, 0.72, 0.84), uNight);
    baseColor += rimColor * meniscus * (0.10 + shimmer * 0.10) * (1.0 - uStorm * 0.5);

    if (uRain > 0.1) {
      float splash = pow(noise(vec2(x * 0.32, floor(uTime * 5.0) * 1.7)), 10.0) * meniscus;
      baseColor += vec3(0.75, 0.90, 0.94) * splash * uRain * 0.55;
    }

    float alpha = mix(0.32, 0.72, pow(normDepth, 0.8)) * surfaceEdge;
    alpha = clamp(alpha + meniscus * 0.10, 0.0, 0.82);

    gl_FragColor = vec4(baseColor, alpha);
  }
`;

export const WATER_FORE_FRAGMENT_SHADER = /* glsl */ `
  precision highp float;
  uniform float uTime;
  uniform float uSurfaceSceneY;
  uniform float uWindFactor;
  uniform float uNight;
  uniform float uStorm;
  uniform sampler2D uNormalMap;
  varying vec2 vScenePos;

  float causticLight(vec2 p, float t) {
    vec2 p1 = p * vec2(0.024, 0.040) + vec2(-t * 0.10, t * 0.05);
    vec2 p2 = p * vec2(0.033, 0.022) + vec2(t * 0.08, -t * 0.07);
    float w1 = sin(p1.x * 2.5 + sin(p1.y * 2.1 + t) * 0.85);
    float w2 = cos(p2.y * 2.6 - sin(p2.x * 1.9 - t * 0.6) * 0.8);
    return pow(clamp(1.0 - abs(w1 + w2) * 0.55, 0.0, 1.0), 4.8);
  }

  void main() {
    float x = vScenePos.x;
    float y = vScenePos.y;
    float waveSpeed = 0.28 + uWindFactor * 0.20;
    float waveAmp = 0.16 + uWindFactor * 0.14;
    float surfaceY = uSurfaceSceneY + sin(x * 0.031 - uTime * waveSpeed) * waveAmp;
    float depth = surfaceY - y;
    if (depth < 0.0) discard;

    float waterSpan = max(40.0, surfaceY - (-250.0));
    float normDepth = clamp(depth / waterSpan, 0.0, 1.0);

    float flowSpeed = 0.015 + uWindFactor * 0.010;
    vec2 nUv = vScenePos * vec2(0.004, 0.008) - vec2(uTime * flowSpeed, uTime * 0.002);
    vec2 flowPerturb = texture2D(uNormalMap, nUv).xy * 2.0 - 1.0;

    float c = causticLight(vec2(x + depth * 0.12, y * 1.2) + flowPerturb * 7.0, uTime * 0.45);
    float fade = exp(-normDepth * 2.3) * (1.0 - uStorm * 0.65) * smoothstep(0.0, 4.0, depth);
    float glint = pow(max(0.0, flowPerturb.x * 0.6 + flowPerturb.y * 0.8), 5.0) * exp(-normDepth * 1.9) * 0.045;

    vec3 tint = mix(vec3(0.64, 0.94, 0.95), vec3(0.38, 0.68, 0.84), uNight);
    float intensity = (c * fade * mix(0.09, 0.04, uNight)) + glint;

    gl_FragColor = vec4(tint * intensity, clamp(intensity, 0.0, 0.32));
  }
`;
