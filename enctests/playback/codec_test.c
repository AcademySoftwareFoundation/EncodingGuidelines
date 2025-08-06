#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <time.h>
#include <libavcodec/avcodec.h>
#include <libavformat/avformat.h>
#include <libavutil/timestamp.h>
#include <libswscale/swscale.h>

#define ADDITIONAL_FRAMES 100

double get_time(void) {
    struct timespec ts;
    clock_gettime(CLOCK_MONOTONIC, &ts);
    return ts.tv_sec + ts.tv_nsec / 1e9;
}

int decode_frames_with_library(const char* filename, const char* decoder_library, int64_t seek_frame) {
    AVFormatContext* format_ctx = NULL;
    AVCodecContext* codec_ctx = NULL;
    const AVCodec* codec = NULL;
    AVFrame* frame = NULL;
    AVPacket* packet = NULL;
    int video_stream_index = -1;
    int ret;

    if (avformat_open_input(&format_ctx, filename, NULL, NULL) < 0) {
        fprintf(stderr, "Could not open file %s\n", filename);
        return -1;
    }

    if (avformat_find_stream_info(format_ctx, NULL) < 0) {
        fprintf(stderr, "Could not find stream information\n");
        avformat_close_input(&format_ctx);
        return -1;
    }

    for (unsigned int i = 0; i < format_ctx->nb_streams; i++) {
        if (format_ctx->streams[i]->codecpar->codec_type == AVMEDIA_TYPE_VIDEO) {
            video_stream_index = i;
            break;
        }
    }

    if (video_stream_index == -1) {
        fprintf(stderr, "Could not find video stream\n");
        avformat_close_input(&format_ctx);
        return -1;
    }

    AVCodecParameters* codecpar = format_ctx->streams[video_stream_index]->codecpar;

    codec = avcodec_find_decoder_by_name(decoder_library);
    if (!codec) {
        fprintf(stderr, "Decoder library %s not found\n", decoder_library);
        avformat_close_input(&format_ctx);
        return -1;
    }

    if (codec->id != codecpar->codec_id) {
        fprintf(stderr, "Specified decoder library %s does not match the video codec\n", decoder_library);
        avformat_close_input(&format_ctx);
        return -1;
    }

    codec_ctx = avcodec_alloc_context3(codec);
    if (!codec_ctx) {
        fprintf(stderr, "Could not allocate codec context\n");
        avformat_close_input(&format_ctx);
        return -1;
    }
    

    if (avcodec_parameters_to_context(codec_ctx, codecpar) < 0) {
        fprintf(stderr, "Could not copy codec parameters to context\n");
        avcodec_free_context(&codec_ctx);
        avformat_close_input(&format_ctx);
        return -1;
    }
    // Set threading options
    codec_ctx->thread_count = 0; // Let FFmpeg decide the number of threads
    // codec_ctx->thread_type = FF_THREAD_FRAME; // | FF_THREAD_SLICE; // Use both frame and slice threading
    // codec_ctx->flags2 |= AV_CODEC_FLAG2_FAST;
    // codec_ctx->flags |= AV_CODEC_FLAG_LOW_DELAY;

    if (avcodec_open2(codec_ctx, codec, NULL) < 0) {
        fprintf(stderr, "Could not open codec\n");
        avcodec_free_context(&codec_ctx);
        avformat_close_input(&format_ctx);
        return -1;
    }

    frame = av_frame_alloc();
    packet = av_packet_alloc();
    if (!frame || !packet) {
        fprintf(stderr, "Could not allocate frame or packet\n");
        av_frame_free(&frame);
        av_packet_free(&packet);
        avcodec_free_context(&codec_ctx);
        avformat_close_input(&format_ctx);
        return -1;
    }

    // Convert frame number to timestamp
    AVStream* video_stream = format_ctx->streams[video_stream_index];
    int64_t seek_timestamp = av_rescale_q(seek_frame, 
                                          av_inv_q(video_stream->avg_frame_rate), 
                                          video_stream->time_base);



    int frames_decoded = 0;
    double total_decoding_time = 0.0;
    double first_frame_time = 0.0;
    clock_t start_time = clock();
    double seek_start = get_time();


    if (av_seek_frame(format_ctx, video_stream_index, seek_timestamp, AVSEEK_FLAG_BACKWARD) < 0) {
        fprintf(stderr, "Error while seeking\n");
        av_frame_free(&frame);
        av_packet_free(&packet);
        avcodec_free_context(&codec_ctx);
        avformat_close_input(&format_ctx);
        return -1;
    }

    avcodec_flush_buffers(codec_ctx);

    double seek_end = get_time();
    printf("SeekTime: %.3f\n", seek_end - seek_start);

    clock_t end_time = clock();
    double frame_time = ((double) (end_time - start_time)) / CLOCKS_PER_SEC;
    fprintf(stderr, "Decoder seek: %s\nFirstFrame: %.6f\n", decoder_library, frame_time);
    start_time = clock();
    struct timespec start_time2;
    clock_gettime(CLOCK_MONOTONIC, &start_time2);
    double start_decode = get_time();


    while (av_read_frame(format_ctx, packet) >= 0 && frames_decoded <= ADDITIONAL_FRAMES) {
        clock_t end_time = clock();
        double frame_time = ((double) (end_time - start_time)) / CLOCKS_PER_SEC;
        fprintf(stderr, "avread_frame: %.6f\n", frame_time);
        if (packet->stream_index == video_stream_index) {
            
            clock_t send_start_time = clock();
            ret = avcodec_send_packet(codec_ctx, packet);
            if (ret < 0) {
                fprintf(stderr, "Error sending packet for decoding\n");
                break;
            }

            clock_t end_time = clock();
            double frame_time = ((double) (end_time - send_start_time)) / CLOCKS_PER_SEC;
            fprintf(stderr, "send_packet: %.6f\n", frame_time);

            while (ret >= 0) {
                clock_t receive_time_start = clock();
                ret = avcodec_receive_frame(codec_ctx, frame);
                if (ret == AVERROR(EAGAIN) || ret == AVERROR_EOF) {
                    //fprintf(stderr, "ERROR: %d\n", ret);
                    break;
                } else if (ret < 0) {
                    fprintf(stderr, "Error during decoding\n");
                    goto end;
                }

                clock_t end_time = clock();
                double frame_time = ((double) (end_time - start_time)) / CLOCKS_PER_SEC;
                double receive_frame_time = ((double) (end_time - receive_time_start)) / CLOCKS_PER_SEC;
                struct timespec end_time2;
                clock_gettime(CLOCK_MONOTONIC, &end_time2);
                double elapsed_seconds = (end_time2.tv_sec - start_time2.tv_sec) +
                         (end_time2.tv_nsec - start_time2.tv_nsec) / 1e9;
                fprintf(stderr, "Decoder: %s  Frame: %02d  Duration:%.6f ReceiveDuration:%.6f Elapsed:%.6f\n", 
                           decoder_library, frames_decoded, frame_time, receive_frame_time, elapsed_seconds);
                total_decoding_time += frame_time;

                if (frames_decoded == 0) {
                    double first_frame_end = get_time();
                    printf("FirstFrame: %.6f\n", first_frame_end - seek_start);
                    first_frame_time = frame_time;
                    printf("Decoder: %s\nFirstFrameClock: %.6f\n", 
                           decoder_library, frame_time);
                    total_decoding_time = 0;
                    start_time = clock(); // We reset, since we dont want the following times to include the first time.
                }

                frames_decoded++;
                
                if (frames_decoded > ADDITIONAL_FRAMES) {
                    break;
                }
                
                start_time = end_time;  // For timing the next frame
            }
        }
        av_packet_unref(packet);
    }

end:


    if (frames_decoded > 1) {
        double end_decode = get_time();
        double decode_duration = end_decode - start_decode;
        printf("totalDecodeTime: %.6f\n", decode_duration);
        printf("Average: %.6f\n", decode_duration/frames_decoded);
        printf("FPS: %.6f\n", frames_decoded/decode_duration);

        double avg_subsequent_frame_time = (total_decoding_time - first_frame_time) / (frames_decoded - 1);
        printf("AverageClock: %.6f\n", 
               avg_subsequent_frame_time);
    }

    av_frame_free(&frame);
    av_packet_free(&packet);
    avcodec_free_context(&codec_ctx);
    avformat_close_input(&format_ctx);

    return 0;
}

int main(int argc, char* argv[]) {
    if (argc != 4) {
        fprintf(stderr, "Usage: %s <input_file> <decoder_library> <seek_frame>\n", argv[0]);
        return 1;
    }

    const char* input_file = argv[1];
    const char* decoder_library = argv[2];
    int64_t seek_frame = atoll(argv[3]);

    decode_frames_with_library(input_file, decoder_library, seek_frame);

    return 0;
}
