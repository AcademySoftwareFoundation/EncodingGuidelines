class WebGLVideoPlayer {
    constructor(videoElement, canvasElement) {
        this.video = videoElement;
        this.canvas = canvasElement;
        this.gl = this.canvas.getContext('webgl');
        this.isPlaying = false;

        if (!this.gl) {
            console.error('WebGL not supported');
            return;
        }

        this.initGL();
        this.setupTexture();
        this.
            // Bind resize event
            // element resize observer might be better, but window resize is a good start
            window.addEventListener('resize', () => this.resize());
        this.resize(); // initial size
    }

    initGL() {
        const gl = this.gl;

        // Vertex shader
        const vsSource = `
            attribute vec2 a_position;
            attribute vec2 a_texCoord;
            varying vec2 v_texCoord;
            void main() {
                gl_Position = vec4(a_position, 0.0, 1.0);
                v_texCoord = a_texCoord;
            }
        `;

        // Fragment shader
        const fsSource = `
            precision mediump float;
            uniform sampler2D u_image;
            varying vec2 v_texCoord;
            void main() {
                gl_FragColor = texture2D(u_image, v_texCoord);
            }
        `;

        const vertexShader = this.createShader(gl, gl.VERTEX_SHADER, vsSource);
        const fragmentShader = this.createShader(gl, gl.FRAGMENT_SHADER, fsSource);
        this.program = this.createProgram(gl, vertexShader, fragmentShader);

        // Look up locations
        this.positionLocation = gl.getAttribLocation(this.program, "a_position");
        this.texCoordLocation = gl.getAttribLocation(this.program, "a_texCoord");

        // Provide texture coordinates for the rectangle.
        const texCoordBuffer = gl.createBuffer();
        gl.bindBuffer(gl.ARRAY_BUFFER, texCoordBuffer);
        // Flip Y for WebGL texture coordinates (0,0 is bottom left, images are top left usually, but for video it depends. 
        // Standard quad:
        // 0.0, 0.0,
        // 1.0, 0.0,
        // 0.0, 1.0,
        // 0.0, 1.0,
        // 1.0, 0.0,
        // 1.0, 1.0,
        // Actually, let's just stick to standard and see if it's flipped. Video textures often need flipY unpixelstorei.

        gl.bufferData(gl.ARRAY_BUFFER, new Float32Array([
            0.0, 0.0,
            1.0, 0.0,
            0.0, 1.0,
            0.0, 1.0,
            1.0, 0.0,
            1.0, 1.0,
        ]), gl.STATIC_DRAW);

        gl.enableVertexAttribArray(this.texCoordLocation);
        gl.vertexAttribPointer(this.texCoordLocation, 2, gl.FLOAT, false, 0, 0);

        // Create a buffer for the positions.
        const positionBuffer = gl.createBuffer();
        gl.bindBuffer(gl.ARRAY_BUFFER, positionBuffer);
        // Full clip space quad
        gl.bufferData(gl.ARRAY_BUFFER, new Float32Array([
            -1.0, 1.0,
            1.0, 1.0,
            -1.0, -1.0,
            -1.0, -1.0,
            1.0, 1.0,
            1.0, -1.0,
        ]), gl.STATIC_DRAW);

        gl.enableVertexAttribArray(this.positionLocation);
        gl.vertexAttribPointer(this.positionLocation, 2, gl.FLOAT, false, 0, 0);
    }

    createShader(gl, type, source) {
        const shader = gl.createShader(type);
        gl.shaderSource(shader, source);
        gl.compileShader(shader);
        if (!gl.getShaderParameter(shader, gl.COMPILE_STATUS)) {
            console.error(gl.getShaderInfoLog(shader));
            gl.deleteShader(shader);
            return null;
        }
        return shader;
    }

    createProgram(gl, vertexShader, fragmentShader) {
        const program = gl.createProgram();
        gl.attachShader(program, vertexShader);
        gl.attachShader(program, fragmentShader);
        gl.linkProgram(program);
        if (!gl.getProgramParameter(program, gl.LINK_STATUS)) {
            console.error(gl.getProgramInfoLog(program));
            gl.deleteProgram(program);
            return null;
        }
        return program;
    }

    setupTexture() {
        const gl = this.gl;
        this.texture = gl.createTexture();
        gl.bindTexture(gl.TEXTURE_2D, this.texture);

        // Set the parameters so we can render any size image.
        gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_WRAP_S, gl.CLAMP_TO_EDGE);
        gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_WRAP_T, gl.CLAMP_TO_EDGE);
        gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_MIN_FILTER, gl.LINEAR);
        gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_MAG_FILTER, gl.LINEAR);
    }

    resize() {
        // Match canvas size to video size (or container size)
        // For now, let's match the video's display size.
        // Actually, we want resolution to match video resolution for best quality, 
        // but css size to match container.
        // Let's use videoWidth/Height for internal resolution.

        if (this.video.videoWidth) {
            this.canvas.width = this.video.videoWidth;
            this.canvas.height = this.video.videoHeight;
            this.gl.viewport(0, 0, this.gl.canvas.width, this.gl.canvas.height);
        }
    }

    start() {
        if (this.isPlaying) return;
        this.isPlaying = true;
        this.render();
    }

    stop() {
        this.isPlaying = false;
    }

    render() {
        if (!this.isPlaying) return;

        const gl = this.gl;

        // Check if video is ready
        if (this.video.readyState >= this.video.HAVE_CURRENT_DATA) {
            // Resize if needed (e.g. if video metadata just loaded)
            if (this.canvas.width !== this.video.videoWidth || this.canvas.height !== this.video.videoHeight) {
                this.resize();
            }

            gl.useProgram(this.program);
            gl.bindTexture(gl.TEXTURE_2D, this.texture);

            // Flip Y for video texture if needed? usually flipY is false by default.
            // But traditionally WebGL 0,0 is bottom-left, images top-left.
            // Let's try pixelStorei UNPACK_FLIP_Y_WEBGL = true
            gl.pixelStorei(gl.UNPACK_FLIP_Y_WEBGL, true);

            gl.texImage2D(gl.TEXTURE_2D, 0, gl.RGBA, gl.RGBA, gl.UNSIGNED_BYTE, this.video);

            gl.drawArrays(gl.TRIANGLES, 0, 6);
        }

        if (this.video.requestVideoFrameCallback) {
            this.video.requestVideoFrameCallback(this.render.bind(this));
        } else {
            requestAnimationFrame(this.render.bind(this));
        }
    }
}
