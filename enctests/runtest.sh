python3 -m testframework.main --source-folder sources/enc_sources --test-config test_configs/prores_tests.yml --output prores-results.otio --encoded-folder prores-encode

python3 -m testframework.otio2html --test-config test_configs/prores_tests.yml --results prores-results.otio

python3 -m testframework.main --source-folder sources/enc_sources --test-config test_configs/h264_tests.yml --output h264-results.otio --encoded-folder h264-encode

python3 -m testframework.otio2html --test-config test_configs/h264_tests.yml --results h264-results.otio

python3 -m testframework.main --source-folder sources/enc_sources --test-config test_configs/h264_crf_tests.yml --output h264-crf-results.otio --encoded-folder h264-crf-encode

python3 -m testframework.otio2html --test-config test_configs/h264_crf_tests.yml --results h264-crf-results.otio

python3 -m testframework.main --source-folder sources/enc_sources --test-config test_configs/color_tests.yml --output color-results.otio --encoded-folder color-encode
python3 -m testframework.main --source-folder sources/enc_sources --test-config test_configs/hevc_color_tests.yml --output hevc-color-results.otio --encoded-folder hevc-color-encode

python3 -m testframework.main --source-folder sources/enc_sources --test-config test_configs/av1_color_tests.yml --output av1-color-results.otio --encoded-folder av1-color-encode
python3 -m testframework.main --source-folder sources/enc_sources --test-config test_configs/dnxhd_color_tests.yml --output dnxhd-color-results.otio --encoded-folder dnxhd-color-encode

python3 -m testframework.generatetests

python3 -m testframework.main --test-config test_configs/documentation_tests.yml --output doc-results.otio --encoded-folder docs-encode
python3 -m testframework.otio2html --test-config test_configs/documentation_tests.yml --results doc-results.otio
