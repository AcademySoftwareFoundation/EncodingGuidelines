#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <time.h>

#include <libavcodec/avcodec.h>
#include <libavformat/avformat.h>
#include <libavutil/timestamp.h>
#include <libswscale/swscale.h>

#define ADDITIONAL_FRAMES 30

double get_time() {
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

    for (int i = 0; i < format_ctx->nb_streams; i++) {
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

    if (av_seek_frame(format_ctx, video_stream_index, seek_timestamp, AVSEEK_FLAG_BACKWARD) < 0) {
        fprintf(stderr, "Error while seeking\n");
        av_frame_free(&frame);
        av_packet_free(&packet);
        avcodec_free_context(&codec_ctx);
        avformat_close_input(&format_ctx);
        return -1;
    }

    avcodec_flush_buffers(codec_ctx);

    int frames_decoded = 0;
    double total_decoding_time = 0.0;
    double first_frame_time = 0.0;

    while (av_read_frame(format_ctx, packet) >= 0 && frames_decoded <= ADDITIONAL_FRAMES) {
        if (packet->stream_index == video_stream_index) {
            double start_time = get_time();

            ret = avcodec_send_packet(codec_ctx, packet);
            if (ret < 0) {
                fprintf(stderr, "Error sending packet for decoding\n");
                break;
            }

            while (ret >= 0) {
                ret = avcodec_receive_frame(codec_ctx, frame);
                if (ret == AVERROR(EAGAIN) || ret == AVERROR_EOF) {
                    break;
                } else if (ret < 0) {
                    fprintf(stderr, "Error during decoding\n");
                    goto end;
                }

                double end_time = get_time();
                double frame_time = end_time - start_time;
                total_decoding_time += frame_time;

                if (frames_decoded == 0) {
                    first_frame_time = frame_time;
                    printf("Decoder: %s\nFirstFrame: %.6f\n", 
                           decoder_library, frame_time);
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
        double avg_subsequent_frame_time = (total_decoding_time - first_frame_time) / (frames_decoded - 1);
        printf("Average: %.6f\n", 
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