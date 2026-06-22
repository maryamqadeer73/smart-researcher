import os
import json
import time
import base64
import tempfile
import requests
from pathlib import Path

# ── PLATFORM PUBLISHERS ─────────────────────────────────────────────────────

def upload_to_linkedin(access_token: str, person_urn: str, caption: str, image_paths: list) -> dict:
    """
    Publishes a multi-image carousel post (or single image) to LinkedIn
    using the UGC Post API (User Generated Content).
    Returns: {"ok": True/False, "post_id": "...", "error": "..."}
    """
    headers = {
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/json",
        "X-Restli-Protocol-Version": "2.0.0"
    }

    # Step 1: Register each image as a LinkedIn Asset
    asset_urns = []
    for img_path in image_paths:
        register_payload = {
            "registerUploadRequest": {
                "recipes": ["urn:li:digitalmediaRecipe:feedshare-image"],
                "owner": person_urn,
                "serviceRelationships": [{
                    "relationshipType": "OWNER",
                    "identifier": "urn:li:userGeneratedContent"
                }]
            }
        }
        reg_res = requests.post(
            "https://api.linkedin.com/v2/assets?action=registerUpload",
            headers=headers,
            json=register_payload,
            timeout=20
        )
        if reg_res.status_code != 200:
            return {"ok": False, "error": f"LinkedIn asset registration failed: {reg_res.text}"}

        reg_data = reg_res.json()
        upload_url = reg_data["value"]["uploadMechanism"]["com.linkedin.digitalmedia.uploading.MediaUploadHttpRequest"]["uploadUrl"]
        asset_urn = reg_data["value"]["asset"]

        # Step 2: Upload the actual image binary
        with open(img_path, "rb") as img_file:
            upload_res = requests.put(
                upload_url,
                headers={"Authorization": f"Bearer {access_token}"},
                data=img_file,
                timeout=30
            )
        if upload_res.status_code not in [200, 201]:
            return {"ok": False, "error": f"LinkedIn image upload failed: {upload_res.text}"}

        asset_urns.append(asset_urn)
        time.sleep(1)  # Brief pause between uploads

    # Step 3: Create the post with the uploaded images
    media_list = [
        {
            "status": "READY",
            "description": {"text": f"Slide {i + 1}"},
            "media": urn,
            "title": {"text": f"Slide {i + 1}"}
        }
        for i, urn in enumerate(asset_urns)
    ]

    post_payload = {
        "author": person_urn,
        "lifecycleState": "PUBLISHED",
        "specificContent": {
            "com.linkedin.ugc.ShareContent": {
                "shareCommentary": {"text": caption},
                "shareMediaCategory": "IMAGE",
                "media": media_list
            }
        },
        "visibility": {
            "com.linkedin.ugc.MemberNetworkVisibility": "PUBLIC"
        }
    }

    post_res = requests.post(
        "https://api.linkedin.com/v2/ugcPosts",
        headers=headers,
        json=post_payload,
        timeout=20
    )
    if post_res.status_code == 201:
        post_id = post_res.headers.get("x-restli-id", "")
        return {"ok": True, "post_id": post_id}
    else:
        return {"ok": False, "error": f"LinkedIn post failed: {post_res.text}"}


def upload_to_instagram(access_token: str, ig_user_id: str, caption: str, image_paths: list, image_urls: list = None) -> dict:
    """
    Publishes a carousel post to Instagram using the Meta Content Publishing API.
    NOTE: Instagram requires publicly-accessible image URLs, not local file paths.
    We use the image_urls list (pre-uploaded URLs) or a fallback temporary image host.
    Returns: {"ok": True/False, "post_id": "...", "error": "..."}
    """
    base_url = f"https://graph.facebook.com/v18.0/{ig_user_id}"
    params_base = {"access_token": access_token}

    # Use provided image_urls OR fall back to a placeholder
    if not image_urls:
        return {"ok": False, "error": "Instagram requires public image URLs. Please provide image_urls."}

    if len(image_urls) == 1:
        # Single image post
        create_res = requests.post(
            f"{base_url}/media",
            params={**params_base, "image_url": image_urls[0], "caption": caption},
            timeout=20
        )
        data = create_res.json()
        if "id" not in data:
            return {"ok": False, "error": f"Instagram media creation failed: {data}"}
        creation_id = data["id"]

        publish_res = requests.post(
            f"{base_url}/media_publish",
            params={**params_base, "creation_id": creation_id},
            timeout=20
        )
        pub_data = publish_res.json()
        if "id" in pub_data:
            return {"ok": True, "post_id": pub_data["id"]}
        return {"ok": False, "error": f"Instagram publish failed: {pub_data}"}
    else:
        # Carousel: create individual item containers first
        item_ids = []
        for url in image_urls:
            item_res = requests.post(
                f"{base_url}/media",
                params={**params_base, "image_url": url, "is_carousel_item": True},
                timeout=20
            )
            item_data = item_res.json()
            if "id" not in item_data:
                return {"ok": False, "error": f"Instagram carousel item creation failed: {item_data}"}
            item_ids.append(item_data["id"])
            time.sleep(1)

        # Create carousel container
        carousel_res = requests.post(
            f"{base_url}/media",
            params={
                **params_base,
                "media_type": "CAROUSEL",
                "caption": caption,
                "children": ",".join(item_ids)
            },
            timeout=20
        )
        carousel_data = carousel_res.json()
        if "id" not in carousel_data:
            return {"ok": False, "error": f"Instagram carousel container failed: {carousel_data}"}

        # Publish
        publish_res = requests.post(
            f"{base_url}/media_publish",
            params={**params_base, "creation_id": carousel_data["id"]},
            timeout=20
        )
        pub_data = publish_res.json()
        if "id" in pub_data:
            return {"ok": True, "post_id": pub_data["id"]}
        return {"ok": False, "error": f"Instagram carousel publish failed: {pub_data}"}


def compile_slides_to_video(image_paths: list, output_path: str, fps: int = 1, duration_per_slide: int = 3) -> str:
    """
    Compiles a list of slide PNG images into an MP4 video (for YouTube Shorts / TikTok).
    Uses imageio with the bundled ffmpeg backend.
    """
    try:
        import imageio
        import numpy as np
        from PIL import Image

        TARGET_W, TARGET_H = 1080, 1920  # Portrait aspect ratio for Shorts/TikTok

        writer = imageio.get_writer(
            output_path,
            fps=fps * duration_per_slide,
            codec="libx264",
            quality=8,
            macro_block_size=None
        )

        for img_path in image_paths:
            img = Image.open(img_path).convert("RGB")
            # Scale + pad to portrait aspect ratio
            img.thumbnail((TARGET_W, TARGET_H), Image.LANCZOS)
            canvas = Image.new("RGB", (TARGET_W, TARGET_H), (18, 18, 27))
            x = (TARGET_W - img.width) // 2
            y = (TARGET_H - img.height) // 2
            canvas.paste(img, (x, y))
            frame = np.array(canvas)
            for _ in range(fps * duration_per_slide):
                writer.append_data(frame)

        writer.close()
        return output_path
    except Exception as e:
        raise RuntimeError(f"Video compilation failed: {e}")


def upload_to_youtube(refresh_token: str, client_id: str, client_secret: str,
                      title: str, description: str, video_path: str) -> dict:
    """
    Uploads a video to YouTube using the YouTube Data API v3.
    Returns: {"ok": True/False, "video_id": "...", "error": "..."}
    """
    # Step 1: Refresh access token
    token_res = requests.post(
        "https://oauth2.googleapis.com/token",
        data={
            "client_id": client_id,
            "client_secret": client_secret,
            "refresh_token": refresh_token,
            "grant_type": "refresh_token"
        },
        timeout=15
    )
    token_data = token_res.json()
    if "access_token" not in token_data:
        return {"ok": False, "error": f"YouTube token refresh failed: {token_data}"}

    access_token = token_data["access_token"]

    # Step 2: Upload video using resumable upload
    metadata = {
        "snippet": {
            "title": title[:100],
            "description": description[:5000],
            "tags": ["TechWithMaryam", "Tech", "AI", "Shorts"],
            "categoryId": "28"  # Technology category
        },
        "status": {
            "privacyStatus": "public",
            "selfDeclaredMadeForKids": False
        }
    }

    # Initiate upload
    init_res = requests.post(
        "https://www.googleapis.com/upload/youtube/v3/videos?uploadType=resumable&part=snippet,status",
        headers={
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json",
            "X-Upload-Content-Type": "video/mp4"
        },
        json=metadata,
        timeout=20
    )

    if init_res.status_code != 200:
        return {"ok": False, "error": f"YouTube upload initiation failed: {init_res.text}"}

    upload_url = init_res.headers.get("Location")
    if not upload_url:
        return {"ok": False, "error": "YouTube: No upload URL returned"}

    # Step 3: Upload the actual video binary
    with open(video_path, "rb") as vf:
        video_data = vf.read()

    upload_res = requests.put(
        upload_url,
        headers={
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "video/mp4",
            "Content-Length": str(len(video_data))
        },
        data=video_data,
        timeout=120
    )

    if upload_res.status_code in [200, 201]:
        video_info = upload_res.json()
        return {"ok": True, "video_id": video_info.get("id", "")}
    else:
        return {"ok": False, "error": f"YouTube upload failed: {upload_res.text}"}


def upload_to_tiktok(access_token: str, caption: str, video_path: str) -> dict:
    """
    Publishes a video to TikTok using the TikTok Content Posting API v2.
    Returns: {"ok": True/False, "publish_id": "...", "error": "..."}
    """
    headers = {
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/json"
    }

    video_size = os.path.getsize(video_path)

    # Step 1: Initialize upload
    init_payload = {
        "post_info": {
            "title": caption[:150],
            "privacy_level": "PUBLIC_TO_EVERYONE",
            "disable_duet": False,
            "disable_comment": False,
            "disable_stitch": False,
        },
        "source_info": {
            "source": "FILE_UPLOAD",
            "video_size": video_size,
            "chunk_size": video_size,
            "total_chunk_count": 1
        }
    }

    init_res = requests.post(
        "https://open.tiktokapis.com/v2/post/publish/video/init/",
        headers=headers,
        json=init_payload,
        timeout=20
    )
    init_data = init_res.json()

    if init_data.get("error", {}).get("code") != "ok":
        return {"ok": False, "error": f"TikTok init failed: {init_data}"}

    upload_url = init_data["data"]["upload_url"]
    publish_id = init_data["data"]["publish_id"]

    # Step 2: Upload video chunk
    with open(video_path, "rb") as vf:
        chunk_data = vf.read()

    upload_res = requests.put(
        upload_url,
        headers={
            "Content-Type": "video/mp4",
            "Content-Length": str(video_size),
            "Content-Range": f"bytes 0-{video_size - 1}/{video_size}"
        },
        data=chunk_data,
        timeout=120
    )

    if upload_res.status_code not in [200, 201, 206]:
        return {"ok": False, "error": f"TikTok video upload failed: {upload_res.text}"}

    return {"ok": True, "publish_id": publish_id}


def verify_linkedin_token(access_token: str) -> dict:
    """Verify a LinkedIn access token by fetching the user's profile."""
    res = requests.get(
        "https://api.linkedin.com/v2/me",
        headers={"Authorization": f"Bearer {access_token}"},
        timeout=10
    )
    data = res.json()
    if "id" in data:
        name = f"{data.get('localizedFirstName', '')} {data.get('localizedLastName', '')}".strip()
        return {"ok": True, "name": name, "urn": f"urn:li:person:{data['id']}"}
    return {"ok": False, "error": data.get("message", "Invalid token")}


def verify_instagram_token(access_token: str, ig_user_id: str) -> dict:
    """Verify an Instagram token by fetching the account name."""
    res = requests.get(
        f"https://graph.facebook.com/v18.0/{ig_user_id}",
        params={"fields": "name,username", "access_token": access_token},
        timeout=10
    )
    data = res.json()
    if "username" in data or "name" in data:
        return {"ok": True, "name": data.get("name", data.get("username", ""))}
    return {"ok": False, "error": data.get("error", {}).get("message", "Invalid token or User ID")}


def verify_youtube_credentials(refresh_token: str, client_id: str, client_secret: str) -> dict:
    """Verify YouTube credentials by fetching the channel info."""
    token_res = requests.post(
        "https://oauth2.googleapis.com/token",
        data={
            "client_id": client_id,
            "client_secret": client_secret,
            "refresh_token": refresh_token,
            "grant_type": "refresh_token"
        },
        timeout=15
    )
    token_data = token_res.json()
    if "access_token" not in token_data:
        return {"ok": False, "error": f"Token refresh failed: {token_data.get('error_description', '')}"}

    channel_res = requests.get(
        "https://www.googleapis.com/youtube/v3/channels",
        params={"part": "snippet", "mine": True},
        headers={"Authorization": f"Bearer {token_data['access_token']}"},
        timeout=10
    )
    ch_data = channel_res.json()
    if ch_data.get("items"):
        name = ch_data["items"][0]["snippet"]["title"]
        return {"ok": True, "name": name}
    return {"ok": False, "error": "No YouTube channel found for these credentials"}


def verify_tiktok_token(access_token: str) -> dict:
    """Verify a TikTok access token by fetching creator info."""
    res = requests.post(
        "https://open.tiktokapis.com/v2/post/publish/creator_info/query/",
        headers={
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json"
        },
        json={},
        timeout=10
    )
    data = res.json()
    if data.get("error", {}).get("code") == "ok":
        creator = data.get("data", {})
        return {"ok": True, "name": creator.get("creator_username", "Connected")}
    return {"ok": False, "error": data.get("error", {}).get("message", "Invalid TikTok token")}
