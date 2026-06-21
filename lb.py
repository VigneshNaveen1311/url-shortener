from fastapi import FastAPI, HTTPException, Request, Response
import httpx
import itertools
import asyncio

from redis import Redis

app = FastAPI()

r = Redis(host='redis', port=6379, db=1, decode_responses=True)

servers = [
    "http://backend1:8000/",
    "http://backend2:8000/",
    "http://backend3:8000/"
]


async def check_server(server):
    print("Checking!", server, flush=True)
    await asyncio.sleep(5)
    try:
        async with httpx.AsyncClient() as client:
            print("Checking", server, flush=True)
            
            response = await client.get(f"{server}health")
            print("Status:", response.status_code, flush=True)

        r.set(server, 1 if response.status_code == 200 else 0)
    except Exception as e:
        print("Health check failed:", server, repr(e), flush=True)
        r.set(server, 0)

async def health_check():
    while True:
        await asyncio.sleep(60)

        tasks = [check_server(server) for server in servers]
        await asyncio.gather(*tasks)

@app.on_event("startup")
async def startup_event():
    for server in servers:
        if r.get(server) is None:
            r.set(server, 1)
    asyncio.create_task(health_check())


urls = itertools.cycle(servers)


def get_next_server():
    healthy_servers = sum(int(r.get(server)) for server in servers)
    print("Healthy count =", healthy_servers, flush=True)
    instance = next(urls)
    if healthy_servers > 0:
        while int(r.get(instance)) != 1:
            print("Trying server:", instance, flush=True)
            instance = next(urls)
    else:
        raise HTTPException(
            status_code=503,
            detail="No healthy backend servers available"
        )
    
    return instance


async def forward_requests(url: str, method, headers, body):
    print("Trying connection to ", url)
    try:
        async with httpx.AsyncClient() as client:
            response = await client.request(
                method=method,
                url=url,
                headers=headers,
                content=body
            )
    except httpx.ConnectError:
        print("Request ", url, " Failed")
        raise HTTPException(status_code=503)
    
    return response


@app.api_route("/", methods=["GET"])
@app.api_route("/{catchall:path}",methods=["GET","POST"])
async def reverse_proxy(request:Request, catchall:str = ""):
    
    retries = sum(int(r.get(server)) for server in servers)
    body = await request.body()
    headers = dict(request.headers)
    headers.pop("host", None) #dont want to forward localhost
    print("BODY =", body, flush = True)
    print("HEADERS =", headers, flush = True)
    while retries>0:
        instance = get_next_server()
        print(request.url, flush = True)
        try:
            response = await forward_requests(
                url=instance+catchall,
                method=request.method,
                headers=headers,
                body=body
            )
            return Response(
                content=response.content,
                status_code=response.status_code,
                headers=dict(response.headers)
            )
        except HTTPException as e:
            if e.status_code == 503:
                r.set(instance, 0)
                retries -= 1
                continue

            raise #when its not 503 raise the exception
    
    raise HTTPException(
        status_code=503,
        detail="No healthy backend servers"
    )
