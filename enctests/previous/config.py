testconfigs = [
    {
        'testname': 'scale_yuv444p10le',
        'description': 'scale (yuv444p10le)',
        'ffmpeg_args': [
            '-c:v libx264',
            '-preset placebo',
            '-qp 0',
            '-x264-params "keyint=15:no-deblock=1"',
            '-pix_fmt yuv444p10le',
            '-sws_flags spline+accurate_rnd+full_chroma_int',
            '-vf "scale=in_range=full:in_color_matrix=bt709:out_range=tv:out_color_matrix=bt709"',
            '-color_range 1',
            '-colorspace 1',
            '-color_primaries 1',
            '-color_trc 2'
        ]
    },
    {
        'testname': 'colorspace_rgb',
        'description': 'colorspace_rgb',
        'testmask': '../sourceimages/1920px-SMPTE_Color_Bars_16x9-edges.png',
        'ffmpeg_args': [
            '-c:v libx264',
            '-preset slow',
            '-crf 18',
            '-x264-params "keyint=15:no-deblock=1"'
        ]
    },
    {
        'testname': 'colorspace_yuv420p_slow_crf_23',
        'description': 'colorspace_yuv420p crf 23',
        'ffmpeg_args': [
            '-c:v libx264',
            '-preset slow',
            '-crf 18',
            '-x264-params "keyint=15:no-deblock=1"',
            '-pix_fmt yuv420p',
            '-sws_flags spline+accurate_rnd+full_chroma_int',
            '-vf "scale=in_range=full:in_color_matrix=bt709:out_range=tv:out_color_matrix=bt709"',
            '-color_range 1',
            '-colorspace 1',
            '-color_primaries 1',
            '-color_trc 2'
        ]
    },
    {
        'testname': 'colorspace_yuv420p_slower_crf_18',
        'description': 'colorspace_yuv420p slower crf 18',
        'ffmpeg_args': [
            '-c:v libx264',
            '-preset slower',
            '-crf 18',
            '-x264-params "keyint=15:no-deblock=1"',
            '-pix_fmt yuv420p',
            '-sws_flags spline+accurate_rnd+full_chroma_int',
            '-vf "scale=in_range=full:in_color_matrix=bt709:out_range=tv:out_color_matrix=bt709"',
            '-color_range 1',
            '-colorspace 1',
            '-color_primaries 1',
            '-color_trc 2'
        ]
    },
    {
        'testname': 'colorspace_yuv420p_slower_film_crf_18',
        'description': 'colorspace_yuv420p tune=film crf 18',
        'ffmpeg_args': [
            '-c:v libx264',
            '-preset slower',
            '-tune film',
            '-crf 18',
            '-x264-params "keyint=15:no-deblock=1"',
            '-pix_fmt yuv420p',
            '-sws_flags spline+accurate_rnd+full_chroma_int',
            '-vf "scale=in_range=full:in_color_matrix=bt709:out_range=tv:out_color_matrix=bt709"',
            '-color_range 1',
            '-colorspace 1',
            '-color_primaries 1',
            '-color_trc 2'
        ]
    },
    {
        'testname': 'colorspace_yuv420pfull',
        'description': 'colorspace_yuv420p',
        'ffmpeg_args': [
            '-c:v libx264',
            '-preset slow',
            '-crf 18',
            '-x264-params "keyint=15:no-deblock=1" -pix_fmt yuv420p',
            '-sws_flags spline+accurate_rnd+full_chroma_int',
            '-vf "scale=in_range=full:in_color_matrix=bt709:out_range=full:out_color_matrix=bt709"',
            '-color_range 2',
            '-colorspace 1',
            '-color_primaries 1',
            '-color_trc 1'
        ]
    },
    {
        'testname': 'shotgun_diy_encode',
        'description': 'From https://support.shotgunsoftware.com/hc/en-us/articles/219030418-Do-it-yourself-DIY-transcoding',
        'testmask': '../sourceimages/1920px-SMPTE_Color_Bars_16x9-edges.png',
        'ffmpeg_args': [
            '-vcodec libx264',
            '-pix_fmt yuv420p',
            '-g 30',
            '-vprofile high',
            '-bf 0',
            '-crf 2'
        ]
    },
    {
        'testname': 'wdi-mpeg2',
        'testmask': '../sourceimages/1920px-SMPTE_Color_Bars_16x9-edges.png',
        'ffmpeg_args': [
            '-vcodec mpeg2video',
            '-profile:v 4',
            '-level:v 4',
            '-b:v 38M',
            '-bt 38M',
            '-q:v 1',
            '-maxrate 38M',
            '-pix_fmt yuv420p',
            '-vf colormatrix=bt601:bt709'
        ]
    },
    {
        'testname': 'wdi-prores444_scale',
        'ffmpeg_args': [
            '-c:v prores_ks',
            '-profile:v 4444',
            '-qscale:v 1',
            '-vendor ap10',
            '-pix_fmt yuv444p10le',
            '-sws_flags spline+accurate_rnd+full_chroma_int',
            '-vf "scale=in_range=full:in_color_matrix=bt709:out_range=tv:out_color_matrix=bt709"',
            '-color_range 1',
            '-colorspace 1',
            '-color_primaries 1',
            '-color_trc 2'
        ]
    }
]

testfiles = [
    {
        'source_file': 'sources/SMPTE_Color_Bars.png',
        'output_file': 'colorbars.mov',
        'stillframe': True,
        'vmaf_reference': 'scale_yuv444p10le',
        'ffmpeg_extract': [
            '-compression_level 10',
            '-pred mixed',
            '-pix_fmt rgb24',
            '-sws_flags +accurate_rnd+full_chroma_int'
        ]
        #'testmask': '1920px-SMPTE_Color_Bars_16x9-edges.png',
    },
    {
        'source_file': 'sources/1080p/sintel_trailer_2k_%04d.png',
        'input_args': [
            '-r 24',
            '-start_number 600'
        ],
        'vframes': '-vframes 75',
        'output_file': 'trailer.mov',
        'stillframe': False,
        'start_number': 600,
        'duration': 75,
        'vmaf_reference': 'scale_yuv444p10le',
        'ffmpeg_extract': [
            '-compression_level 10',
            '-pred mixed',
            '-pix_fmt rgb24',
            '-sws_flags +accurate_rnd+full_chroma_int'
        ]
        #'testmask': '1920px-SMPTE_Color_Bars_16x9-edges.png',
    },
    {
        'source_file': 'sources/1080p/sintel_trailer_2k_0620.png',
        'output_file': 'trailerstill.mov',
        'stillframe': True,
        'vmaf_reference': 'scale_yuv444p10le',
        'ffmpeg_extract': [
            '-compression_level 10',
            '-pred mixed',
            '-pix_fmt rgb24',
            '-sws_flags +accurate_rnd+full_chroma_int'
        ]
        #'testmask': '1920px-SMPTE_Color_Bars_16x9-edges.png',
    }
]
