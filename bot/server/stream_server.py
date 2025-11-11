from aiohttp import web
from bot.telegram import StreamBot

async def media_streamer(request):
    try:
        message_id = int(request.query.get("id"))
        chat_id = int(request.match_info.get("encodedname"))
        return await _media_streamer(request, message_id, chat_id)
    except Exception as e:
        return web.Response(text=f"Error: {e}", status=500)

async def _media_streamer(request, message_id: int, chat_id: int):
    range_header = request.headers.get("Range", 0)

    media_msg = await StreamBot.get_messages(chat_id, message_id)
    file_properties = await StreamBot.get_file_properties(media_msg)
    file_size = file_properties.file_size

    if range_header:
        from_bytes, until_bytes = range_header.replace("bytes=", "").split("-")
        from_bytes = int(from_bytes)
        until_bytes = int(until_bytes) if until_bytes else file_size - 1
    else:
        from_bytes = 0
        until_bytes = file_size - 1

    req_length = until_bytes - from_bytes

    new_chunk_size = 1048576  # 1MB
    offset = from_bytes - (from_bytes % new_chunk_size)

    first_part_cut = from_bytes - offset
    last_part_cut = until_bytes % new_chunk_size + 1

    chunk_size = new_chunk_size + (0 if first_part_cut == 0 else new_chunk_size)

    body = StreamBot.stream_media(
        media_msg,
        offset=offset,
        limit=chunk_size // 1024,
    )

    data = b""
    async for chunk in body:
        data += chunk

    data = data[first_part_cut:last_part_cut]

    return web.Response(
        body=data,
        status=206 if range_header else 200,
        headers={
            "Content-Type": file_properties.mime_type,
            "Content-Range": f"bytes {from_bytes}-{until_bytes}/{file_size}",
            "Content-Length": str(req_length),
            "Accept-Ranges": "bytes",
        },
    )
