/* _quads.c */
#define PY_SSIZE_T_CLEAN
#include <Python.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#ifdef _WIN32
#define WIN32_LEAN_AND_MEAN
#include <windows.h>
#endif

typedef unsigned int  GLenum;
typedef unsigned int  GLuint;
typedef int           GLint;
typedef float         GLfloat;
typedef int           GLsizei;
typedef unsigned char GLboolean;
typedef ptrdiff_t     GLsizeiptr;
typedef ptrdiff_t     GLintptr;

#define GL_FLOAT                0x1406
#define GL_FALSE                0
#define GL_ARRAY_BUFFER         0x8892
#define GL_ELEMENT_ARRAY_BUFFER 0x8893
#define GL_DYNAMIC_DRAW         0x88E8
#define GL_TRIANGLES            0x0004
#define GL_UNSIGNED_INT         0x1405
#define GL_TEXTURE_2D           0x0DE1
#define GL_BLEND                0x0BE2
#define GL_SRC_ALPHA            0x0302
#define GL_ONE_MINUS_SRC_ALPHA  0x0303
#define GL_VERTEX_SHADER        0x8B31
#define GL_FRAGMENT_SHADER      0x8B30
#define GL_COMPILE_STATUS       0x8B81
#define GL_LINK_STATUS          0x8B82
#define GL_TEXTURE0             0x84C0

typedef void   (*PFNGLBINDBUFFERPROC)(GLenum, GLuint);
typedef void   (*PFNGLBUFFERDATAPROC)(GLenum, GLsizeiptr, const void *, GLenum);
typedef void   (*PFNGLBUFFERSUBDATAPROC)(GLenum, GLintptr, GLsizeiptr, const void *);
typedef void   (*PFNGLGENBUFFERSPROC)(GLsizei, GLuint *);
typedef void   (*PFNGLDELETEBUFFERSPROC)(GLsizei, const GLuint *);
typedef void   (*PFNGLGENVERTEXARRAYSPROC)(GLsizei, GLuint *);
typedef void   (*PFNGLBINDVERTEXARRAYPROC)(GLuint);
typedef void   (*PFNGLDELETEVERTEXARRAYSPROC)(GLsizei, const GLuint *);
typedef void   (*PFNGLENABLEVERTEXATTRIBARRAYPROC)(GLuint);
typedef void   (*PFNGLVERTEXATTRIBPOINTERPROC)(GLuint, GLint, GLenum, GLboolean, GLsizei, const void *);
typedef void   (*PFNGLDRAWELEMENTSPROC)(GLenum, GLsizei, GLenum, const void *);
typedef void   (*PFNGLBINDTEXTUREPROC)(GLenum, GLuint);
typedef void   (*PFNGLENABLEPROC)(GLenum);
typedef void   (*PFNGLBLENDFUNCPROC)(GLenum, GLenum);
typedef void   (*PFNGLACTIVETEXTUREPROC)(GLenum);
typedef GLuint (*PFNGLCREATEPROGRAMPROC)(void);
typedef GLuint (*PFNGLCREATESHADERPROC)(GLenum);
typedef void   (*PFNGLSHADERSOURCEPROC)(GLuint, GLsizei, const char **, const GLint *);
typedef void   (*PFNGLCOMPILESHADERPROC)(GLuint);
typedef void   (*PFNGLATTACHSHADERPROC)(GLuint, GLuint);
typedef void   (*PFNGLLINKPROGRAMPROC)(GLuint);
typedef void   (*PFNGLUSEPROGRAMPROC)(GLuint);
typedef void   (*PFNGLDELETESHADERPROC)(GLuint);
typedef void   (*PFNGLDELETEPROGRAMPROC)(GLuint);
typedef GLint  (*PFNGLGETUNIFORMLOCATIONPROC)(GLuint, const char *);
typedef void   (*PFNGLUNIFORM1FPROC)(GLuint, GLfloat);
typedef void   (*PFNGLUNIFORM2FPROC)(GLuint, GLfloat, GLfloat);
typedef void   (*PFNGLUNIFORM4FVPROC)(GLuint, GLsizei, const GLfloat *);
typedef void   (*PFNGLGETSHADERIVPROC)(GLuint, GLenum, GLint *);
typedef void   (*PFNGLGETPROGRAMIVPROC)(GLuint, GLenum, GLint *);
typedef void   (*PFNGLGETSHADERINFOLOGPROC)(GLuint, GLsizei, GLsizei *, char *);

static PFNGLBINDBUFFERPROC              gl_BindBuffer              = NULL;
static PFNGLBUFFERDATAPROC              gl_BufferData              = NULL;
static PFNGLBUFFERSUBDATAPROC           gl_BufferSubData           = NULL;
static PFNGLGENBUFFERSPROC              gl_GenBuffers              = NULL;
static PFNGLDELETEBUFFERSPROC           gl_DeleteBuffers           = NULL;
static PFNGLGENVERTEXARRAYSPROC         gl_GenVertexArrays         = NULL;
static PFNGLBINDVERTEXARRAYPROC         gl_BindVertexArray         = NULL;
static PFNGLDELETEVERTEXARRAYSPROC      gl_DeleteVertexArrays      = NULL;
static PFNGLENABLEVERTEXATTRIBARRAYPROC gl_EnableVertexAttribArray = NULL;
static PFNGLVERTEXATTRIBPOINTERPROC     gl_VertexAttribPointer     = NULL;
static PFNGLDRAWELEMENTSPROC            gl_DrawElements            = NULL;
static PFNGLBINDTEXTUREPROC             gl_BindTexture             = NULL;
static PFNGLENABLEPROC                  gl_Enable                  = NULL;
static PFNGLBLENDFUNCPROC               gl_BlendFunc               = NULL;
static PFNGLCREATEPROGRAMPROC           gl_CreateProgram           = NULL;
static PFNGLCREATESHADERPROC            gl_CreateShader            = NULL;
static PFNGLSHADERSOURCEPROC            gl_ShaderSource            = NULL;
static PFNGLCOMPILESHADERPROC           gl_CompileShader           = NULL;
static PFNGLATTACHSHADERPROC            gl_AttachShader            = NULL;
static PFNGLLINKPROGRAMPROC             gl_LinkProgram             = NULL;
static PFNGLUSEPROGRAMPROC              gl_UseProgram              = NULL;
static PFNGLDELETESHADERPROC            gl_DeleteShader            = NULL;
static PFNGLDELETEPROGRAMPROC           gl_DeleteProgram           = NULL;
static PFNGLGETUNIFORMLOCATIONPROC      gl_GetUniformLocation      = NULL;
static PFNGLUNIFORM1FPROC               gl_Uniform1f               = NULL;
static PFNGLUNIFORM2FPROC               gl_Uniform2f               = NULL;
static PFNGLUNIFORM4FVPROC              gl_Uniform4fv              = NULL;
static PFNGLGETSHADERIVPROC             gl_GetShaderiv             = NULL;
static PFNGLGETPROGRAMIVPROC            gl_GetProgramiv            = NULL;
static PFNGLGETSHADERINFOLOGPROC        gl_GetShaderInfoLog        = NULL;
static PFNGLACTIVETEXTUREPROC           gl_ActiveTexture           = NULL;

/*
 * Vertex layout (16 floats):
 *  0-1  : cell_top_x, cell_top_y
 *  2    : atlas_idx (-1 = bg-only)
 *  3-6  : fg rgba (0-255)
 *  7-10 : bg rgba (0-255)
 *  11   : bold_u8 (0-255)
 *  12   : mode (0=bg, 1=glyph)
 *  13   : skew_u8 (0-255, 128=no skew)
 *  14   : scale_x
 *  15   : scale_y
 */
#define VERT_STRIDE      16
#define INITIAL_QUADS    65536
#define MAX_UV_GLYPHS    256

static GLuint g_vao          = 0;
static GLuint g_vbo          = 0;
static GLuint g_ibo          = 0;
static int    g_vbo_capacity = 0;
static int    g_ibo_capacity = 0;
static GLuint g_sdf_prog     = 0;
static GLint  g_loc_vp            = -1;
static GLint  g_loc_edge          = -1;
static GLint  g_loc_cw            = -1;
static GLint  g_loc_ch            = -1;
static GLint  g_loc_draw_size     = -1;
static GLint  g_loc_cell_w_atlas  = -1;
static GLint  g_loc_cell_h_atlas  = -1;
static GLint  g_loc_baseline_row  = -1;
static GLint  g_loc_ascent_px     = -1;
static GLint  g_loc_descent_px    = -1;
static GLint  g_loc_sdf_padding   = -1;
static GLint  g_loc_uv            = -1;

static char *read_file(const char *path) {
    FILE *f = fopen(path, "rb");
    if (!f) { fprintf(stderr, "_quads: cannot open %s\n", path); return NULL; }
    fseek(f, 0, SEEK_END);
    long sz = ftell(f);
    rewind(f);
    char *buf = (char *)malloc(sz + 1);
    if (!buf) { fclose(f); return NULL; }
    fread(buf, 1, sz, f);
    buf[sz] = '\0';
    fclose(f);
    return buf;
}

static GLuint compile_shader(GLenum type, const char *src) {
    GLuint s = gl_CreateShader(type);
    gl_ShaderSource(s, 1, &src, NULL);
    gl_CompileShader(s);
    GLint ok = 0;
    gl_GetShaderiv(s, GL_COMPILE_STATUS, &ok);
    if (!ok) {
        char buf[512];
        gl_GetShaderInfoLog(s, 512, NULL, buf);
        fprintf(stderr, "_quads shader error: %s\n", buf);
    }
    return s;
}

static int build_program(const char *shader_dir) {
    char vert_path[512], frag_path[512];
    snprintf(vert_path, sizeof(vert_path), "%s/sdf_quad.vert", shader_dir);
    snprintf(frag_path, sizeof(frag_path), "%s/sdf_quad.frag", shader_dir);
    char *vs = read_file(vert_path);
    char *fs = read_file(frag_path);
    if (!vs || !fs) { free(vs); free(fs); return 0; }
    GLuint v = compile_shader(GL_VERTEX_SHADER, vs);
    GLuint f = compile_shader(GL_FRAGMENT_SHADER, fs);
    free(vs); free(fs);
    g_sdf_prog = gl_CreateProgram();
    gl_AttachShader(g_sdf_prog, v);
    gl_AttachShader(g_sdf_prog, f);
    gl_LinkProgram(g_sdf_prog);
    gl_DeleteShader(v);
    gl_DeleteShader(f);
    GLint ok = 0;
    gl_GetProgramiv(g_sdf_prog, GL_LINK_STATUS, &ok);
    if (!ok) { fprintf(stderr, "_quads: link failed\n"); return 0; }
    g_loc_vp           = gl_GetUniformLocation(g_sdf_prog, "u_vp");
    g_loc_edge         = gl_GetUniformLocation(g_sdf_prog, "u_edge");
    g_loc_cw           = gl_GetUniformLocation(g_sdf_prog, "u_cw");
    g_loc_ch           = gl_GetUniformLocation(g_sdf_prog, "u_ch");
    g_loc_draw_size    = gl_GetUniformLocation(g_sdf_prog, "u_draw_size");
    g_loc_cell_w_atlas = gl_GetUniformLocation(g_sdf_prog, "u_cell_w_atlas");
    g_loc_cell_h_atlas = gl_GetUniformLocation(g_sdf_prog, "u_cell_h_atlas");
    g_loc_baseline_row = gl_GetUniformLocation(g_sdf_prog, "u_baseline_row");
    g_loc_ascent_px    = gl_GetUniformLocation(g_sdf_prog, "u_ascent_px");
    g_loc_descent_px   = gl_GetUniformLocation(g_sdf_prog, "u_descent_px");
    g_loc_sdf_padding  = gl_GetUniformLocation(g_sdf_prog, "u_sdf_padding");
    g_loc_uv           = gl_GetUniformLocation(g_sdf_prog, "u_uv");
    return 1;
}

static void ensure_ibo(int n_quads) {
    if (n_quads <= g_ibo_capacity) return;
    int cap = n_quads + 4096;
    unsigned int *idx = (unsigned int *)malloc((size_t)cap * 6 * sizeof(unsigned int));
    for (int i = 0; i < cap; i++) {
        unsigned int b = (unsigned int)(i * 4);
        idx[i*6+0]=b; idx[i*6+1]=b+1; idx[i*6+2]=b+2;
        idx[i*6+3]=b; idx[i*6+4]=b+2; idx[i*6+5]=b+3;
    }
    gl_BindBuffer(GL_ELEMENT_ARRAY_BUFFER, g_ibo);
    gl_BufferData(GL_ELEMENT_ARRAY_BUFFER,
                  (GLsizeiptr)((size_t)cap * 6 * sizeof(unsigned int)),
                  idx, GL_DYNAMIC_DRAW);
    free(idx);
    g_ibo_capacity = cap;
    fprintf(stderr, "_quads: IBO grown to %d quads\n", cap);
}

static void setup_attribs(void) {
    GLsizei stride = VERT_STRIDE * (GLsizei)sizeof(float);
    gl_EnableVertexAttribArray(0);
    gl_VertexAttribPointer(0, 2, GL_FLOAT, GL_FALSE, stride, (void*)( 0*sizeof(float)));
    gl_EnableVertexAttribArray(1);
    gl_VertexAttribPointer(1, 1, GL_FLOAT, GL_FALSE, stride, (void*)( 2*sizeof(float)));
    gl_EnableVertexAttribArray(2);
    gl_VertexAttribPointer(2, 4, GL_FLOAT, GL_FALSE, stride, (void*)( 3*sizeof(float)));
    gl_EnableVertexAttribArray(3);
    gl_VertexAttribPointer(3, 4, GL_FLOAT, GL_FALSE, stride, (void*)( 7*sizeof(float)));
    gl_EnableVertexAttribArray(4);
    gl_VertexAttribPointer(4, 1, GL_FLOAT, GL_FALSE, stride, (void*)(11*sizeof(float)));
    gl_EnableVertexAttribArray(5);
    gl_VertexAttribPointer(5, 1, GL_FLOAT, GL_FALSE, stride, (void*)(12*sizeof(float)));
    gl_EnableVertexAttribArray(6);
    gl_VertexAttribPointer(6, 1, GL_FLOAT, GL_FALSE, stride, (void*)(13*sizeof(float)));
    gl_EnableVertexAttribArray(7);
    gl_VertexAttribPointer(7, 1, GL_FLOAT, GL_FALSE, stride, (void*)(14*sizeof(float)));
    gl_EnableVertexAttribArray(8);
    gl_VertexAttribPointer(8, 1, GL_FLOAT, GL_FALSE, stride, (void*)(15*sizeof(float)));
}

static void setup_vao(void) {
    gl_GenVertexArrays(1, &g_vao);
    gl_GenBuffers(1, &g_vbo);
    gl_GenBuffers(1, &g_ibo);

    gl_BindVertexArray(g_vao);

    gl_BindBuffer(GL_ARRAY_BUFFER, g_vbo);
    gl_BufferData(GL_ARRAY_BUFFER,
                  (GLsizeiptr)((size_t)INITIAL_QUADS * 4 * VERT_STRIDE * sizeof(float)),
                  NULL, GL_DYNAMIC_DRAW);
    g_vbo_capacity = INITIAL_QUADS;

    setup_attribs();

    gl_BindBuffer(GL_ELEMENT_ARRAY_BUFFER, g_ibo);
    ensure_ibo(INITIAL_QUADS);

    gl_BindVertexArray(0);
}

static PyObject *
init_ffi_ptrs(PyObject *self, PyObject *args)
{
    unsigned long long a0,a1,a2,a3,a4,a5;
    if (!PyArg_ParseTuple(args, "KKKKKK", &a0,&a1,&a2,&a3,&a4,&a5))
        return NULL;
    Py_RETURN_NONE;
}

static PyObject *
init_gl_ptrs(PyObject *self, PyObject *args)
{
    PyObject   *loader;
    const char *shader_dir;
    if (!PyArg_ParseTuple(args, "Os", &loader, &shader_dir)) return NULL;

#define LOAD(var, name) do { \
    PyObject *r = PyObject_CallFunction(loader, "s", name); \
    if (!r) return NULL; \
    unsigned long long v = PyLong_AsUnsignedLongLong(r); \
    Py_DECREF(r); \
    if (PyErr_Occurred()) return NULL; \
    var = (void*)(uintptr_t)v; \
    if (!var) { \
        PyErr_Format(PyExc_RuntimeError, "_quads: failed to load %s", name); \
        return NULL; \
    } \
} while(0)

    LOAD(gl_BindBuffer,              "glBindBuffer");
    LOAD(gl_BufferData,              "glBufferData");
    LOAD(gl_BufferSubData,           "glBufferSubData");
    LOAD(gl_GenBuffers,              "glGenBuffers");
    LOAD(gl_DeleteBuffers,           "glDeleteBuffers");
    LOAD(gl_GenVertexArrays,         "glGenVertexArrays");
    LOAD(gl_BindVertexArray,         "glBindVertexArray");
    LOAD(gl_DeleteVertexArrays,      "glDeleteVertexArrays");
    LOAD(gl_EnableVertexAttribArray, "glEnableVertexAttribArray");
    LOAD(gl_VertexAttribPointer,     "glVertexAttribPointer");
    LOAD(gl_DrawElements,            "glDrawElements");
    LOAD(gl_BindTexture,             "glBindTexture");
    LOAD(gl_Enable,                  "glEnable");
    LOAD(gl_BlendFunc,               "glBlendFunc");
    LOAD(gl_CreateProgram,           "glCreateProgram");
    LOAD(gl_CreateShader,            "glCreateShader");
    LOAD(gl_ShaderSource,            "glShaderSource");
    LOAD(gl_CompileShader,           "glCompileShader");
    LOAD(gl_AttachShader,            "glAttachShader");
    LOAD(gl_LinkProgram,             "glLinkProgram");
    LOAD(gl_UseProgram,              "glUseProgram");
    LOAD(gl_DeleteShader,            "glDeleteShader");
    LOAD(gl_DeleteProgram,           "glDeleteProgram");
    LOAD(gl_GetUniformLocation,      "glGetUniformLocation");
    LOAD(gl_Uniform1f,               "glUniform1f");
    LOAD(gl_Uniform2f,               "glUniform2f");
    LOAD(gl_Uniform4fv,              "glUniform4fv");
    LOAD(gl_GetShaderiv,             "glGetShaderiv");
    LOAD(gl_GetProgramiv,            "glGetProgramiv");
    LOAD(gl_GetShaderInfoLog,        "glGetShaderInfoLog");
    LOAD(gl_ActiveTexture,           "glActiveTexture");
#undef LOAD

    if (!build_program(shader_dir)) {
        PyErr_SetString(PyExc_RuntimeError, "_quads: shader build failed");
        return NULL;
    }
    setup_vao();
    Py_RETURN_NONE;
}

static PyObject *
draw_sdf_quads(PyObject *self, PyObject *args)
{
    PyObject    *buf_obj;
    PyObject    *uv_obj;
    int          n;
    unsigned int tex_id;
    float        vp_w, vp_h, edge;
    float        cw, ch, draw_size;
    float        cell_w_atlas, cell_h_atlas, baseline_row;
    float        ascent_px, descent_px, sdf_padding;

    /* args: staging_buf, n_quads, tex_id,
             vp_w, vp_h, edge,
             cw, ch, draw_size,
             cell_w_atlas, cell_h_atlas, baseline_row,
             ascent_px, descent_px, sdf_padding,
             uv_buf
       format: O i I f f f f f f f f f f f f O
               1 2 3 4 5 6 7 8 9 0 1 2 3 4 5 6  = 16 items, 12 floats */
    if (!PyArg_ParseTuple(args, "OiIffffffffffffO",
                          &buf_obj, &n, &tex_id,
                          &vp_w, &vp_h, &edge,
                          &cw, &ch, &draw_size,
                          &cell_w_atlas, &cell_h_atlas, &baseline_row,
                          &ascent_px, &descent_px, &sdf_padding,
                          &uv_obj))
        return NULL;

    if (!g_sdf_prog) {
        PyErr_SetString(PyExc_RuntimeError, "_quads: call init_gl_ptrs first");
        return NULL;
    }
    if (n <= 0) Py_RETURN_NONE;

    Py_buffer view, uv_view;
    if (PyObject_GetBuffer(buf_obj, &view, PyBUF_SIMPLE) < 0)
        return NULL;
    if (PyObject_GetBuffer(uv_obj, &uv_view, PyBUF_SIMPLE) < 0) {
        PyBuffer_Release(&view);
        return NULL;
    }

    GLsizeiptr upload_bytes = (GLsizeiptr)((size_t)n * 4 * VERT_STRIDE * sizeof(float));

    gl_BindVertexArray(g_vao);

    if (n > g_vbo_capacity) {
        int cap = n + 4096;
        gl_BindBuffer(GL_ARRAY_BUFFER, g_vbo);
        gl_BufferData(GL_ARRAY_BUFFER,
                      (GLsizeiptr)((size_t)cap * 4 * VERT_STRIDE * sizeof(float)),
                      NULL, GL_DYNAMIC_DRAW);
        setup_attribs();
        g_vbo_capacity = cap;
        fprintf(stderr, "_quads: VBO grown to %d quads\n", cap);
    }

    if (n > g_ibo_capacity)
        ensure_ibo(n);

    gl_BindBuffer(GL_ARRAY_BUFFER, g_vbo);
    gl_BufferSubData(GL_ARRAY_BUFFER, 0, upload_bytes, view.buf);
    gl_BindBuffer(GL_ARRAY_BUFFER, 0);

    gl_UseProgram(g_sdf_prog);
    gl_Uniform2f(g_loc_vp,           vp_w, vp_h);
    gl_Uniform1f(g_loc_edge,         edge);
    gl_Uniform1f(g_loc_cw,           cw);
    gl_Uniform1f(g_loc_ch,           ch);
    gl_Uniform1f(g_loc_draw_size,    draw_size);
    gl_Uniform1f(g_loc_cell_w_atlas, cell_w_atlas);
    gl_Uniform1f(g_loc_cell_h_atlas, cell_h_atlas);
    gl_Uniform1f(g_loc_baseline_row, baseline_row);
    gl_Uniform1f(g_loc_ascent_px,    ascent_px);
    gl_Uniform1f(g_loc_descent_px,   descent_px);
    gl_Uniform1f(g_loc_sdf_padding,  sdf_padding);

    int n_uv = (int)(uv_view.len / (4 * sizeof(float)));
    if (n_uv > MAX_UV_GLYPHS) n_uv = MAX_UV_GLYPHS;
    gl_Uniform4fv(g_loc_uv, n_uv, (const GLfloat *)uv_view.buf);

    gl_ActiveTexture(GL_TEXTURE0);
    gl_BindTexture(GL_TEXTURE_2D, tex_id);

    gl_Enable(GL_BLEND);
    gl_BlendFunc(GL_SRC_ALPHA, GL_ONE_MINUS_SRC_ALPHA);

    gl_DrawElements(GL_TRIANGLES, n * 6, GL_UNSIGNED_INT, 0);

    gl_BindVertexArray(0);
    gl_BindTexture(GL_TEXTURE_2D, 0);
    gl_UseProgram(0);

    PyBuffer_Release(&view);
    PyBuffer_Release(&uv_view);
    Py_RETURN_NONE;
}

static PyObject *
draw_bg_rects(PyObject *self, PyObject *args)
{
    Py_RETURN_NONE;
}

static PyObject *
shutdown_gl(PyObject *self, PyObject *args)
{
    if (g_vao) { gl_DeleteVertexArrays(1, &g_vao); g_vao = 0; }
    if (g_vbo) { gl_DeleteBuffers(1, &g_vbo); g_vbo = 0; }
    if (g_ibo) { gl_DeleteBuffers(1, &g_ibo); g_ibo = 0; }
    if (g_sdf_prog) { gl_DeleteProgram(g_sdf_prog); g_sdf_prog = 0; }
    Py_RETURN_NONE;
}

static PyMethodDef QuadsMethods[] = {
    {"init_ffi_ptrs",  init_ffi_ptrs,  METH_VARARGS, NULL},
    {"init_gl_ptrs",   init_gl_ptrs,   METH_VARARGS, NULL},
    {"draw_sdf_quads", draw_sdf_quads, METH_VARARGS, NULL},
    {"draw_bg_rects",  draw_bg_rects,  METH_VARARGS, NULL},
    {"shutdown_gl",    shutdown_gl,    METH_VARARGS, NULL},
    {NULL, NULL, 0, NULL}
};

static struct PyModuleDef quadsmodule = {
    PyModuleDef_HEAD_INIT, "_quads", NULL, -1, QuadsMethods
};

PyMODINIT_FUNC PyInit__quads(void) {
    return PyModule_Create(&quadsmodule);
}
