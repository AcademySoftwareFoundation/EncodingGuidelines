python3 -m testframework.main --source-folder sources/enc_sources --test-config test_configs/prores_tests.yml --output prores-results.otio --encoded-folder prores-encode
python3 -m testframework.main --source-folder sources/enc_sources --test-config test_configs/prores_qscale_tests.yml --output prores-qscale-results.otio --encoded-folder prores-qscale-encode

python3 -m testframework.otio2html --test-config test_configs/prores_tests.yml --results prores-results.otio

python3 -m testframework.main --source-folder sources/enc_sources --test-config test_configs/codec_tests.yml --output codec-results.otio --encoded-folder codec-encode

python3 -m testframework.main --source-folder sources/enc_sources --test-config test_configs/h264_tests.yml --output h264-results.otio --encoded-folder h264-encode

python3 -m testframework.otio2html --test-config test_configs/h264_tests.yml --results h264-results.otio

python3 -m testframework.main --source-folder sources/enc_sources --test-config test_configs/h264_crf_tests.yml --output h264-crf-results.otio --encoded-folder h264-crf-encode

python3 -m testframework.otio2html --test-config test_configs/h264_crf_tests.yml --results h264-crf-results.otio

python3 -m testframework.main --source-folder sources/enc_sources --test-config test_configs/color_tests.yml --output color-results.otio --encoded-folder color-encode
python3 -m testframework.main --source-folder sources/enc_sources --test-config test_configs/hevc_color_tests.yml --output hevc-color-results.otio --encoded-folder hevc-color-encode

python3 -m testframework.main --source-folder sources/enc_sources --test-config test_configs/rgb_color_tests.yml --output rgb-color-results.otio --encoded-folder rgb-color-encode

python3 -m testframework.main --source-folder sources/enc_sources --test-config test_configs/rgb_tests.yml --output rgb-results.otio --encoded-folder rgb-encode

python3 -m testframework.main --source-folder sources/enc_sources --test-config test_configs/mjpeg_color_tests.yml --output mjpeg-color-results.otio --encoded-folder mjpeg-color-encode

python3 -m testframework.main --source-folder sources/enc_sources --test-config test_configs/av1_color_tests.yml --output av1-color-results.otio --encoded-folder av1-color-encode

python3 -m testframework.main --source-folder sources/enc_sources --test-config test_configs/vp9_color_tests.yml --output vp9-color-results.otio --encoded-folder vp9-color-encode


python3 -m testframework.main --source-folder sources/enc_sources --test-config test_configs/dnxhd_color_tests.yml --output dnxhd-color-results.otio --encoded-folder dnxhd-color-encode
python3 -m testframework.main --source-folder sources/enc_sources --test-config test_configs/dnxhd_tests.yml --output dnxhd-results.otio --encoded-folder dnxhd-encode

python3 -m testframework.main --source-folder sources/enc_sources --test-config test_configs/hevc_tests.yml --output hevc-results.otio --encoded-folder hevc-encode
python3 -m testframework.main --source-folder sources/enc_sources --test-config test_configs/av1_crf_tests.yml --output av1-crf-results.otio --encoded-folder av1-crf-encode

python3 -m testframework.main --source-folder sources/enc_sources --test-config test_configs/hevc_crf_tests.yml --output hevc-crf-results.otio --encoded-folder hevc-crf-encode
python3 -m testframework.otio2html --test-config test_configs/hevc_crf_tests.yml --results hevc-crf-results.otio

python3 -m testframework.main --source-folder sources/enc_sources --test-config test_configs/color_tests.yml --output color-results.otio --encoded-folder color-encode

# Windows only with nvenc
python -m testframework.main --source-folder sources/enc_sources --test-config test_configs/hevc_nvenc_color_tests.yml --output hevc-nvenc-color-results.otio --encoded-folder hevc-color-encode
python -m testframework.main --source-folder sources/enc_sources --test-config test_configs/hevc_nvenc_tests.yml --output hevc-nvenc-results.otio --encoded-folder hevc-nvenc-encode
python -m testframework.otio2html --test-config test_configs/hevc_nvenc_tests.yml --results hevc-nvenc-results.otio

# OSX Only tests
python -m testframework.main --source-folder sources/enc_sources --test-config test_configs/osx_prores_tests.yml --output osx-prores-results.otio --encoded-folder osx-prores-encode


#WIP
python3 -m testframework.generatetests

python3 -m testframework.main --test-config test_configs/documentation_tests.yml --output doc-results.otio --encoded-folder docs-encode
python3 -m testframework.otio2html --test-config test_configs/documentation_tests.yml --results doc-results.otio
