// sdf_quad.vert
#version 330 core
layout(location=0) in vec2  a_cell;
layout(location=1) in float a_atlas_idx;
layout(location=2) in vec4  a_fg;
layout(location=3) in vec4  a_bg;
layout(location=4) in float a_bold_u8;
layout(location=5) in float a_mode;
layout(location=6) in float a_skew_u8;
layout(location=7) in float a_scale_x;
layout(location=8) in float a_scale_y;

uniform vec2  u_vp;
uniform float u_cw;
uniform float u_ch;
uniform float u_draw_size;
uniform float u_cell_w_atlas;
uniform float u_cell_h_atlas;
uniform float u_baseline_row;
uniform float u_ascent_px;
uniform float u_descent_px;
uniform float u_sdf_padding;
uniform vec4  u_uv[256];

out vec2  v_uv;
out vec4  v_fg;
out vec4  v_bg;
out float v_bold;
out float v_mode;

void main() {
    int corner = int(gl_VertexID) & 3;

    float cx = a_cell.x;
    float cy = a_cell.y;
    float sx = a_scale_x;
    float sy = a_scale_y;

    float px, py;

    if (a_mode < 0.5) {
        // BG quad: simple cell rect
        float w = u_cw * sx;
        float h = u_ch * sy;
        px = cx + ((corner == 2 || corner == 3) ? w : 0.0);
        py = cy + ((corner == 1 || corner == 2) ? h : 0.0);
    } else {
        // Glyph quad: atlas cell, top-left aligned to cell top-left + sdf_padding offset
        float a2s_x = sx * (u_draw_size / 24.0);
        float a2s_y = sy * (u_draw_size / 24.0);

        // baseline_y: cy + (sdf_padding + ascent) * scale
        // glyph_top = baseline_y - baseline_row * scale
        // u_baseline_row == sdf_padding + ascent_px  =>  glyph_top == cy  (exact)
        float baseline_y   = cy + (u_sdf_padding - u_ascent_px) * a2s_y;
        float glyph_top    = baseline_y - u_baseline_row * a2s_y;
        float glyph_bottom = glyph_top  + u_cell_h_atlas * a2s_y;
        float glyph_left   = cx - u_sdf_padding * a2s_x;
        float glyph_right  = glyph_left + u_cell_w_atlas * a2s_x;

        px = (corner == 2 || corner == 3) ? glyph_right : glyph_left;
        py = (corner == 1 || corner == 2) ? glyph_bottom : glyph_top;
    }

    float skew_f  = (a_skew_u8 == 0.0) ? 0.0 : (a_skew_u8 - 128.0) / 127.0;
    float skew_px = skew_f * u_cw * sx;
    float skew_apply = (corner == 0 || corner == 3) ? skew_px : 0.0;

    vec2 ndc = (vec2(px + skew_apply, py) / u_vp) * 2.0 - 1.0;
    ndc.y = -ndc.y;
    gl_Position = vec4(ndc, 0.0, 1.0);

    int idx    = int(a_atlas_idx);
    vec4 uvr   = (idx >= 0) ? u_uv[idx] : vec4(0.0);
    float u    = (corner < 2)                 ? uvr.x : uvr.z;
    float v    = (corner == 0 || corner == 3) ? uvr.y : uvr.w;
    v_uv = vec2(u, v);

    v_bold = 0.48 - (a_bold_u8 / 127.0) * 0.10;
    v_fg   = a_fg;
    v_bg   = a_bg;
    v_mode = a_mode;
}
