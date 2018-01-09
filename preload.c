
#include <dlfcn.h>
#include <stdio.h>
#include <string.h>
#include <libgen.h>
#include <stdlib.h>
#include <curl/curl.h>
#include <stdint.h>

#include <sys/types.h>
#include <sys/stat.h>
#include <unistd.h>

#if defined(RTLD_NEXT)
#define REAL_LIBC RTLD_NEXT
#else
#define REAL_LIBC ((void *) -1L)
#endif

#ifndef BUCKET_URL
#define BUCKET_URL "https://s3-us-west-2.amazonaws.com/pictureweb/conda_shared_libs"
#endif

#ifndef LOCAL_ROOT
#define LOCAL_ROOT "/tmp/condaruntime.lib"
#endif

#ifndef CACHE_SO
#define CACHE_SO 1
#endif


const char* s3_fetch(char* root, char* bucket_url, char* key_name, uint8_t cache) {
    CURL *curl;
    FILE *fp;
    CURLcode res;
    struct stat st = {0};

    printf("root %s bucket_url %s key_name %s \n",  root, bucket_url, key_name);

    uint32_t root_len = strlen(root);
    uint32_t key_len = strlen(key_name);
    uint32_t bucket_len = strlen(bucket_url);
    printf("AFTER STRLEN root %d, key %d, bucket %d\n", root_len, key_len, bucket_len);

    uint32_t out_file_length = root_len + key_len + 2;
    uint32_t s3_key_length = bucket_len + key_len + 2;
    printf("out_file_length %x, s3_key_length %x\n", out_file_length, s3_key_length);

    char* out_file = (char*) malloc(out_file_length);
    char* s3_url = (char*) malloc(s3_key_length);

    snprintf(out_file, out_file_length, "%s/%s", root, key_name);
    snprintf(s3_url, s3_key_length, "%s/%s", bucket_url, key_name);
    curl = curl_easy_init();

    if (cache && stat(out_file, &st) == -1) {
	printf("s3 fetching %s saving to %s\n",  s3_url, out_file);
	if (curl) {
		fp = fopen(out_file,"wb");
		curl_easy_setopt(curl, CURLOPT_URL, s3_url);
		curl_easy_setopt(curl, CURLOPT_WRITEFUNCTION, NULL);
		curl_easy_setopt(curl, CURLOPT_WRITEDATA, fp);
		res = curl_easy_perform(curl);
		/* always cleanup */
		curl_easy_cleanup(curl);
		fclose(fp);
	}
    } else {
	printf("using cached shared library %s\n", out_file);
    }
    return out_file;
}

void* dlopen(const char *file, int mode)
{
    static void* (*o_dlopen) ( const char *file, int mode )=0;
    int len = 0;
    char* base = "";
    char* root = "/home/ubuntu/shared_libs";
    int root_len = strlen(root);
    char* buffer;
    const char* file_to_use;

    struct stat st = {0};

    // create a directory for shared libs
    if (stat(LOCAL_ROOT, &st) == -1) {
	mkdir(LOCAL_ROOT, 0700);
    }

    if (file != NULL && strstr(file, "anaconda") != NULL) {
	base = basename(file);
	file_to_use = s3_fetch(LOCAL_ROOT, BUCKET_URL, base, CACHE_SO);
	/*
	len = strlen(base);
	int new_size = root_len + len + 2;
	buffer = (char*) malloc(new_size);
	snprintf(buffer, new_size, "%s/%s", root, base);
	printf("base: %s\n", base);
	printf("buffer: %s\n", buffer);
	file_to_use = buffer;
	*/
    } else {
	file_to_use = file;
    }
    printf("dlopen %s was called length is %d, base is %s \n", file, len, base);
    o_dlopen = (void*(*)(const char *file, int mode)) dlsym(REAL_LIBC,
	    "dlopen");
    return (*o_dlopen)( file_to_use, mode );
}

