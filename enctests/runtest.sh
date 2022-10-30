python3 -m testframework.main --source-folder sources/encsources --test-config test_configs/prores_tests.yml --output prores-results.otio --encoded-folder prores-encode

python3 -m testframework.otio2html --test-config test_configs/prores_tests.yml --results prores-results.otio

python3 -m testframework.main --source-folder sources/encsources --test-config test_configs/h264_tests.yml --output h264-results.otio --encoded-folder h264-encode

python3 -m testframework.otio2html --test-config test_configs/h264_tests.yml --results h264-results.otio

#WIP
python3 -m testframework.generatetests

 python3 -m testframework.main --test-config test_configs/documentation_tests.yml --output doc-results.otio --encoded-folder docs-encode