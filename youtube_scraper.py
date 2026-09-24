import os
import pandas as pd
from googleapiclient.discovery import build

# ==============================================================================
# PERHATIAN: Masukkan API Key YouTube Anda di sini
# Cara mendapatkan: Buka Google Cloud Console -> Create Project -> Enable 
# 'YouTube Data API v3' -> Credentials -> Create API Key
# ==============================================================================
YOUTUBE_API_KEY = "MASUKKAN_API_KEY_ANDA_DI_SINI"

def get_video_stats_and_comments(video_id, max_comments=8000):
    """
    Fungsi ini mengambil statistik video (Views, Likes) dan komentar
    dari YouTube menggunakan YouTube Data API v3.
    """
    if YOUTUBE_API_KEY == "MASUKKAN_API_KEY_ANDA_DI_SINI":
        print("ERROR: Anda belum memasukkan YOUTUBE_API_KEY di dalam skrip!")
        return None
        
    youtube = build('youtube', 'v3', developerKey=YOUTUBE_API_KEY)
    
    print(f"Mengambil statistik untuk video ID: {video_id}...")
    
    # 1. Ambil Statistik (Views, Likes, Comment Count)
    try:
        video_response = youtube.videos().list(
            part='statistics,snippet',
            id=video_id
        ).execute()
        
        if not video_response['items']:
            print("Video tidak ditemukan.")
            return None
            
        stats = video_response['items'][0]['statistics']
        snippet = video_response['items'][0]['snippet']
        
        print(f"Judul: {snippet['title']}")
        print(f"Views: {stats.get('viewCount', 0)}")
        print(f"Likes: {stats.get('likeCount', 0)}")
        
    except Exception as e:
        print(f"Gagal mengambil statistik: {e}")
        return None

    print(f"\nMengambil target {max_comments} komentar...")
    
    # 2. Ambil Komentar dengan Paginasi
    comments_data = []
    next_page_token = None
    
    while len(comments_data) < max_comments:
        try:
            request = youtube.commentThreads().list(
                part="snippet",
                videoId=video_id,
                maxResults=100, # Maksimal per request dari API
                textFormat="plainText",
                pageToken=next_page_token
            )
            response = request.execute()
            
            for item in response['items']:
                comment = item['snippet']['topLevelComment']['snippet']
                comments_data.append({
                    'video_id': video_id,
                    'author': comment['authorDisplayName'],
                    'published_at': comment['publishedAt'],
                    'like_count': comment['likeCount'],
                    'text': comment['textDisplay']
                })
                
                # Berhenti jika sudah mencapai target
                if len(comments_data) >= max_comments:
                    break
            
            next_page_token = response.get('nextPageToken')
            
            print(f"Berhasil mengunduh {len(comments_data)} komentar...")
            
            if not next_page_token:
                print("Tidak ada lagi halaman komentar (sudah habis).")
                break
                
        except Exception as e:
            print(f"Gagal mengambil komentar (bisa jadi komentar dinonaktifkan): {e}")
            break
            
    df_comments = pd.DataFrame(comments_data)
    
    # Simpan ke CSV
    output_filename = f"youtube_comments_{video_id}.csv"
    df_comments.to_csv(output_filename, index=False)
    print(f"\nSelesai! {len(df_comments)} data komentar berhasil disimpan di '{output_filename}'")
    
    return df_comments

if __name__ == "__main__":
    # Contoh Video ID Trailer KKN di Desa Penari
    # URL: https://www.youtube.com/watch?v=R9zQ66uFvjM -> Video ID: R9zQ66uFvjM
    TARGET_VIDEO_ID = "R9zQ66uFvjM" 
    
    # Target 8000 komentar untuk analisis sentimen
    get_video_stats_and_comments(TARGET_VIDEO_ID, max_comments=8000)
