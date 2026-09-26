import asyncio
from tg_resolver import user_client, resolve_tg_usernames_batch
async def test():
    await user_client.start()
    res = await resolve_tg_usernames_batch(["+79522380687", "+79668484747", "+79136647735"])
    print(res)
asyncio.run(test())
