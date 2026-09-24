import pandas as pd
from itertools import islice
from youtube_comment_downloader import YoutubeCommentDownloader, SORT_BY_POPULAR
import time

def download_youtube_comments(video_id, max_comments=8000):
    """
    Mengunduh komentar YouTube TANPA API KEY menggunakan internal AJAX API.
    Jauh lebih cepat dan ringan daripada Selenium/Playwright.
    """
    print(f"Mulai menyedot komentar dari video ID: {video_id} (Maksimal: {max_comments})...")
    
    downloader = YoutubeCommentDownloader()
    
    # URL video YouTube
    video_url = f"https://www.youtube.com/watch?v={video_id}"
    
    # Menarik komentar (diurutkan dari yang paling populer)
    generator = downloader.get_comments_from_url(video_url, sort_by=SORT_BY_POPULAR)
    
    comments_data = []
    
    try:
        # Mengambil data dari generator sebanyak max_comments
        for comment in islice(generator, max_comments):
            comments_data.append({
                'video_id': video_id,
                'author': comment.get('author', ''),
                'published_at': comment.get('time', ''),
                'like_count': comment.get('votes', 0),
                'text': comment.get('text', '')
            })
            
            # Print progres setiap 500 komentar agar tidak dikira hang
            if len(comments_data) % 500 == 0:
                print(f"[{time.strftime('%H:%M:%S')}] Berhasil mengunduh {len(comments_data)} komentar...")
                
    except Exception as e:
        print(f"Pengunduhan terhenti: {e}")
        
    df = pd.DataFrame(comments_data)
    
    output_filename = f"youtube_comments_{video_id}_no_api.csv"
    df.to_csv(output_filename, index=False)
    
    print(f"\n✅ SUKSES! {len(df)} komentar berhasil disimpan di file: '{output_filename}'")
    return df

if __name__ == "__main__":
    # Ganti dengan ID video yang Anda inginkan
    # Contoh Trailer KKN di Desa Penari: R9zQ66uFvjM
    TARGET_VIDEO_ID = "R9zQ66uFvjM"
    
    download_youtube_comments(TARGET_VIDEO_ID, max_comments=8000)
