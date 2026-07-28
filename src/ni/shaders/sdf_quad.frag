// sdf_quad.frag
#version 330 core
in vec2  v_uv;
in vec4  v_fg;
in vec4  v_bg;
in float v_bold;
in float v_mode;

uniform sampler2D u_tex;
uniform float     u_edge;

out vec4 out_color;

const float INV255 = 1.0 / 255.0;

void main() {
    vec4 fg = v_fg * INV255;
    vec4 bg = v_bg * INV255;

    if (v_mode < 0.5) {
        out_color = bg;
        return;
    }
    float d = texture(u_tex, v_uv).a;
    float t = smoothstep(v_bold - u_edge, v_bold + u_edge, d);
    out_color = mix(vec4(bg.rgb, 0.0), fg, t);
}
