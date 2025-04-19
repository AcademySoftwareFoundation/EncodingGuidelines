import subprocess
import time
import json
import os
import re
from datetime import datetime

testdirs = ["../wedge_results/ffmpeg_version_7.1/linux-x86_64/intraframe_tests-encode", 
            "../wedge_results/ffmpeg_version_7.1/linux-x86_64/codec_tests-encode", 
            "../wedge_results/ffmpeg_version_7.1/linux-x86_64/htj2k_options_tests-encode"]

def run_decode_test(input_file, iterations=3):
    """
    Run decode performance test on a video file
    """
    results = []
    
    for i in range(iterations):
        start_time = time.time()
        
        # Run ffmpeg with detailed stats
        cmd = [
            'ffmpeg',
            '-hide_banner',
            '-benchmark',
            '-i', input_file,
            '-f', 'null',
            '-'
        ]
        print("Running:", " ".join(cmd))
        
        process = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            universal_newlines=True
        )
        
        _, stderr = process.communicate()
        
        # Parse the output
        duration = time.time() - start_time
        
        # Extract benchmark info from ffmpeg output
        fps_line = [line for line in stderr.split('\n') if 'fps=' in line]
        print("Got FPS line:", fps_line[-1])
        # Parse something like "frame=  200 fps= 67 q=-0.0 Lsize=N/A time=00:00:08.00 bitrate=N/A speed=2.67x"
        fps_pattern = re.compile(r'fps=\s*(\d+\.?\d*)')
        match = fps_pattern.search(fps_line[-1])
        if match:
            fps = float(match.group(1))
        else:
            fps = "Undefined"
        speed_pattern = re.compile(r'speed=\s*(\d+\.?\d*)x')
        match = speed_pattern.search(fps_line[-1])
        if match:
            speed = float(match.group(1))
        else:
            speed = "Undefined"

        print("SPeed:", speed, " fps:", fps)

        # Extract benchmark info from ffmpeg output
        bench_line = [line for line in stderr.split('\n') if 'bench' in line]
        # Parse something like "bench: utime=2.124s stime=0.069s rtime=2.204s"
        parts = bench_line[0].split()
        times = {}
        for part in parts[1:]:  # Skip 'bench:'
            key, value = part.split('=')
            times[key] = float(value.rstrip('s'))
        
        results.append({
            'iteration': i + 1,
            'fps': fps,
            'speed': speed,
            'duration': times.get('rtime', 0),
            'user_time': times.get('utime', 0),
            'system_time': times.get('stime', 0),
            'real_time': times.get('rtime', 0)
        })
        
        # Small delay between iterations
        time.sleep(1)
    
    return results

def test_multiple_codecs(input_files):
    """
    Test decode performance for multiple input files
    """
    results = {}
    
    for input_file in input_files:
        print(f"\nTesting {input_file}...")
        codec_info = get_codec_info(input_file)
        results[input_file] = {
            'codec_info': codec_info,
            'decode_tests': run_decode_test(input_file)
        }
    
    return results

def get_codec_info(input_file):
    """
    Get codec information for the input file
    """
    cmd = [
        'ffprobe',
        '-v', 'quiet',
        '-print_format', 'json',
        '-show_streams',
        input_file
    ]
    
    process = subprocess.Popen(
        cmd,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        universal_newlines=True
    )
    
    stdout, _ = process.communicate()
    return json.loads(stdout)

def generate_report(results):
    """
    Generate a formatted report of the results
    """
    report = ["Codec Decode Performance Report", "=" * 30, ""]
    
    for file_name, data in results.items():
        report.append(f"\nFile: {file_name}")
        report.append("-" * 50)
        
        # Add codec info
        if 'codec_info' in data and 'streams' in data['codec_info']:
            for stream in data['codec_info']['streams']:
                if stream.get('codec_type') == 'video':
                    report.append(f"Codec: {stream.get('codec_name', 'Unknown')}")
                    report.append(f"Resolution: {stream.get('width', '?')}x{stream.get('height', '?')}")
                    report.append(f"Framerate: {stream.get('r_frame_rate', 'Unknown')}")
        
        # Add decode test results
        report.append("\nDecode Test Results:")
        report.append("Iteration | Duration (s) | Speed | FPS")
        report.append("-" * 40)
        
        avg_duration = 0
        avg_speed = 0
        avg_fps = 0
        tests = data['decode_tests']
        
        for test in tests:
            report.append(f"{test['iteration']:^9} | {test['duration']:^11.3f} | {test['speed']:^5.2f}x | {test['fps']:^5.2f}")
            avg_duration += test['duration']
            avg_fps += test['fps']
            if test['speed']:
                avg_speed += test['speed']
        
        avg_duration /= len(tests)
        avg_speed /= len(tests)
        avg_fps /= len(tests)
        
        report.append("-" * 40)
        report.append(f"Average   | {avg_duration:^11.3f} | {avg_speed:^5.2f}x | {avg_fps:^5.2f}")
        report.append("")
    
    return "\n".join(report)

def main():
    # Example usage
    input_files = []
    for testdir in testdirs:
        input_files.extend([os.path.join(testdir, f) for f in os.listdir(testdir) if f.endswith(".mp4") or f.endswith(".mov")or f.endswith(".mxf")])
    
    results = test_multiple_codecs(input_files)
    report = generate_report(results)
    
    # Save report
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    report_file = f'codec_benchmark_report_{timestamp}.txt'
    
    with open(report_file, 'w') as f:
        f.write(report)
    
    print(report)
    print(f"\nReport saved to: {report_file}")

if __name__ == "__main__":
    main()
