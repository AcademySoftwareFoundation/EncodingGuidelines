python3 -m testframework.generatetests
python3 -m testframework.main 
python3 -m testframework.main --test-config test_wedge_configs --results-folder wedge_results

# python3 -m testframework.otio2html --test-config test_configs/prores_tests.yml --results prores-results.otio


# Windows only with nvenc
#python -m testframework.main --source-folder sources/enc_sources --test-config test_configs/hevc_nvenc_color_tests.yml --output hevc-nvenc-color-results.otio --encoded-folder hevc-color-encode
#python -m testframework.main --source-folder sources/enc_sources --test-config test_configs/hevc_nvenc_tests.yml --output hevc-nvenc-results.otio --encoded-folder hevc-nvenc-encode
#python -m testframework.otio2html --test-config test_configs/hevc_nvenc_tests.yml --results hevc-nvenc-results.otio

# OSX Only tests
#python -m testframework.main --source-folder sources/enc_sources --test-config test_configs/osx_prores_tests.yml --output osx-prores-results.otio --encoded-folder osx-prores-encode


#WIP

#python3 -m testframework.main --test-config test_configs/documentation_tests.yml --output doc-results.otio --encoded-folder docs-encode
#python3 -m testframework.otio2html --test-config test_configs/documentation_tests.yml --results doc-results.otio
