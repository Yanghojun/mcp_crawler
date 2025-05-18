import time
from typing import Optional, Type, TypedDict, Literal
import aiohttp
from pydantic import BaseModel, Field
from dotenv import load_dotenv
load_dotenv()

import os
import requests

from bs4 import BeautifulSoup
import markdownify

from langchain.tools import BaseTool
from langchain.callbacks.manager import (
    CallbackManagerForToolRun,
    AsyncCallbackManagerForToolRun,
)

import certifi
import json
from urllib.request import Request, urlopen
from urllib import parse
import datetime

from typing import Any
import httpx
from mcp.server.fastmcp import FastMCP

import asyncio
from aiohttp import ClientSession

mcp = FastMCP("crawler")

@mcp.tool()
async def get_weather(지역:str):
    """
    대한민국 특정 지역의 날씨를 알려주는 tool 입니다.
    항상 맑음을 반환합니다.

    Args:
        지역: 사용자가 말하는 지역을 의미합니다. (e.g. "서울", "인천")
    """
    return "맑음"

@mcp.tool()
async def get_applyhome_crawl_result(
                               # user_query:str,
                               house_type:str,
                               jiyeok:str):
    """
    대한민국의 아파트의 청약, 민간사전청약아파트, 민간임대오피스텔 등의 정보를 수집할 수 있는 tool입니다.

    Args:
        house_type: 아파트, 민간사전청약아파트, 민간임대오피스텔, 공공지원민간임대 중 선택합니다. 특정 유형을 선택할 수 없다면 '전체'를 선택하세요. (e.g. "전체", "아파트", "민간사전청약아파트", "민간임대오피스텔", "공공지원민간임대")
        jiyeok: 지역 이름을 추출합니다. 특정 지역을 추출할 수 없다면 '전체'를 선택하세요. (e.g. "전체", "서울특별시", "대구광역시", "전라남도", "부산광역시")
    """
    info_url: list = [
        "https://www.applyhome.co.kr/ai/aia/selectAPTLttotPblancDetail.do", # se : 01 or 09
        "https://www.applyhome.co.kr/ai/aia/selectAPTRemndrLttotPblancDetailView.do", # se : 04 or 06 or 11
        "https://www.applyhome.co.kr/ai/aia/selectPRMOLttotPblancDetailView.do"
    ]
    
    data_headers: dict[str, str] = {
        "Content-Type": "application/json",
        "Accept": "application/json, text/javascript, */*; q=0.01",
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/132.0.0.0 Safari/537.36"
    }

    data_url: str = "https://www.applyhome.co.kr/ai/aib/selectSubscrptCalender.do"

    type_keys: dict[str, list] = {
        "아파트": ["01","02", "03", "06", "07", "11"],
        "민간사전청약아파트": ["08", "09", "10"],
        "민간임대오피스텔": ["05"],
        "공공지원민간임대": ["04"],
    }

    jiyeok_keys: dict[str, list] = {
        "서울특별시": ["서울"],
        "광주광역시": ["광주"],
        "대구광역시": ["대구"],
        "대전광역시": ["대전"],
        "부산광역시": ["부산"],
        "세종특별자치시": ["세종"],
        "울산광역시": ["울산"],
        "인천광역시": ["인천"],

        "강원특별자치도": ["강원"],
        "경기도": ["경기"],
        "경상남도": ["경남"],
        "경상북도": ["경북"],
        "전라남도": ["전남"],
        "전라북도": ["전북"],
        "제주특별자치도": ["제주"],
        "충청남도": ["충남"],
        "충청북도": ["충북"],
    }
    
    enum_jiyeok : str = "서울 광주 대구 대전 부산 세종 울산 인천 강원 경기 경북 \
        경남 전남 전북 제주 충남 충북"
    
    async def _start(data_url,
               data_headers):
        async with aiohttp.ClientSession() as session:
            today_yyyymm = datetime.datetime.today().strftime("%Y%m") 
            data_params = {
                "reqData": {
                    "inqirePd": today_yyyymm
                    }
            }
        
            async with session.post(data_url, json=data_params, headers=data_headers) as response:
                response.raise_for_status()
                response_data = await response.json()
                return response_data['schdulList']

        # response = requests.post(data_url, 
        #                          json=data_params, 
        #                          headers=data_headers,
        #                          verify=certifi.where())
        
        # response.raise_for_status()
        # response_data = response.json()
        # data_list = response_data["schdulList"]
        # return data_list
    
    async def _address_api(keyword,
                     **kwargs):
        urls = 'http://www.juso.go.kr/addrlink/addrLinkApi.do'
        confmKey = os.getenv('JUSO_API_KEY') # 필수 값 승인키
        
        params = {
            'keyword': keyword,
            'confmKey': confmKey,
            'resultType': 'json'
        }
        
        if kwargs: # 필수 값이 아닌 변수를 params에 추가
            for key, value in kwargs.items():
                params[key] = value
        params_str = parse.urlencode(params) # dict를 파라미터에 맞는 포맷으로 변경
        
        url = '{}?{}'.format(urls, params_str)

        async with aiohttp.ClientSession() as session:
            async with session.get(urls, params=params) as response:
                result = await response.json()
                status = result['results']['common']['errorMessage']
                roadAddr_list = []
                if status == '정상':
                    for juso in result['results']['juso']:
                        roadAddr_list.append(juso['jibunAddr'])
                return list(set(roadAddr_list))

        response = urlopen(url) # Request 객체로 urlopen을 호출하면 요청된 URL에 대한 응답 객체를 반환
        result_xml = response.read().decode('utf-8') # response를 읽고 utf-8로 변형
        result = json.loads(result_xml)
        status = result['results']['common']['errorMessage']
        roadAddr_list = []
        lengths = len(result['results']['juso'])
        if status == '정상':
            for idx in range(lengths):
                roadAddr_list.append(result['results']['juso'][idx]['jibunAddr'])
        roadAddr_list = set(roadAddr_list)
        return roadAddr_list
    
    async def _transform_address(jiyeok: str) -> list:
        client_id = os.getenv('X_NCP_APIGW_API_KEY_ID')    # 본인이 할당받은 ID 입력
        client_pw = os.getenv('X_NCP_APIGW_API_KEY')    # 본인이 할당받은 Secret 입력
        naver_map_api_url = 'https://naveropenapi.apigw.ntruss.com/map-geocode/v2/geocode?query='
        add_lists = await _address_api(jiyeok)

        result = set()
        for add_list in add_lists:
            add = add_list
            add_urlenc = parse.quote(add)
            url = naver_map_api_url + add_urlenc
            request = Request(url)
            request.add_header('X-NCP-APIGW-API-KEY-ID', client_id)
            request.add_header('X-NCP-APIGW-API-KEY', client_pw)

            response = urlopen(request)
            rescode = response.getcode()
            response_body = response.read().decode('utf-8')
            response_body = json.loads(response_body)

            sido = response_body['addresses'][0]['addressElements'][0]['shortName']
            result.add(sido)
        return list(result)

    def _filtering(
        house_type: list,
        jiyeok: str,
        data_list: list
    ) -> list:
        new_data_list = []
        for data in data_list:
            # 집 필터 / 지역 필터
            if house_type and jiyeok:
                if data['SUBSCRPT_AREA_CODE_NM'] in jiyeok and data['HOUSE_SECD'] in house_type:
                    new_data_list.append(data)
            # 집은 필터 / 지역은 전체
            elif house_type and not jiyeok:
                if data['HOUSE_SECD'] in house_type:
                    new_data_list.append(data)
            # 집은 전체 / 지역은 필터
            elif not house_type and jiyeok:
                if data['SUBSCRPT_AREA_CODE_NM'] in jiyeok:
                    new_data_list.append(data)
            # 집과 지역 전체
            else:
                new_data_list.append(data)

        return new_data_list
    
    async def _download_file(url, file_name):
        async with aiohttp.ClientSession() as session:
            async with session.get(url, ssl=False) as response:
                if response.status == 200:
                    file_name = "./" + file_name
                    content = await response.read()
                    with open(file_name, 'wb') as file:
                        file.write(content)

        # response = requests.get(url, 
        #                         verify=certifi.where())
        # if response.status_code == 200:
        #     file_name = "./" + file_name
        #     with open(file_name, 'wb') as file:
        #         file.write(response.content)

    def _parsing_data(data):
        result = {
            "title": data["HOUSE_NM"],
            "jiyeok": data["SUBSCRPT_AREA_CODE_NM"],
            "date": data["IN_DATE"],
            "house_manage_code": data["HOUSE_MANAGE_NO"],
            "house_pblanc_code": data["PBLANC_NO"],
            "house_secd": data["HOUSE_SECD"]
        }
        
        return result
    
    async def _post_handler(data):
        extract_data = _parsing_data(data)
        # 파일 이름
        file_name = f'{extract_data["title"]}_{extract_data["jiyeok"]}_{extract_data["date"]}.pdf'
        
        # 세부내용 url로 데이터 post
        detail_params = {
            "houseManageNo": extract_data["house_manage_code"],
            "pblancNo": extract_data["house_pblanc_code"],
            "houseSecd": extract_data["house_secd"],
            "gvPgmId": "AIB01M01"
        }
        detail_headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/132.0.0.0 Safari/537.36",
        }
        
        if extract_data["house_secd"] == "01" or extract_data["house_secd"] == "09":
            detail_url = info_url[0]
        elif extract_data["house_secd"] == "04" or extract_data["house_secd"] == "06" or extract_data["house_secd"] == "11":
            detail_url = info_url[1]
        else:
            detail_url = info_url[2]

        async with aiohttp.ClientSession() as session:
            timeout = aiohttp.ClientTimeout(total=30)
            async with session.post(detail_url, data=detail_params, headers=detail_headers, timeout=timeout) as response:
                html_content = await response.text()
                md_content = markdownify.markdownify(html_content)
                
                soup = BeautifulSoup(html_content, 'html.parser')
                link_tag = soup.find("a", class_="radius_btn")
                down_link = link_tag.get("href") if link_tag else None
                
                return {
                    "data_hmno": extract_data,
                    "md_content": md_content,
                    "pdf_url": down_link
                }

        # detail_response = requests.post(detail_url, data=detail_params, headers=detail_headers,
        #                                 verify=certifi.where())
        # md_content = markdownify.markdownify(detail_response.text)

        # detail_response.raise_for_status()
        # soup = BeautifulSoup(detail_response.content, 'html.parser')
        # link_tag = soup.find("a", class_="radius_btn")
        # down_link = link_tag.get("href")
        # # _download_file(down_link, file_name)
        
        # ret = {
        #     "data_hmno": extract_data,
        #     "md_content": md_content, "pdf_url": down_link
        # }
        # return ret
    
    return "Hello World!"

    data_list = await _start(data_url,
                       data_headers)

    house_type_list = []
    jiyeok_list = []
    
    if jiyeok in enum_jiyeok:
        jiyeok_list = [jiyeok]
    else:
        jiyeok = await _transform_address(jiyeok=jiyeok)        
    
    if house_type != "전체":
        h_type_key = type_keys[house_type]
        house_type_list.extend(h_type_key)
    if jiyeok != "전체" and not jiyeok_list:
        for sido in jiyeok: 
            jiyeok_key = jiyeok_keys[sido]
            jiyeok_list.extend(jiyeok_key)

    data_list = _filtering(house_type=house_type_list,
                                jiyeok=jiyeok_list,
                                data_list=data_list)

    posts = await asyncio.gather(
        *[_post_handler(data) for data in data_list]
    )


    # 모든 대기 중인 작업 취소
    tasks = [t for t in asyncio.all_tasks() if t is not asyncio.current_task()]
    
    if not tasks:
        print("✅ 정리할 작업이 없습니다.")
        return
    
    print(f"🔄 {len(tasks)}개의 작업을 취소하는 중...")
    
    for task in tasks:
        task.cancel()

    return posts

async def monitor_tasks():
    while True:
        tasks = [t for t in asyncio.all_tasks() 
                if t is not asyncio.current_task()]
        if tasks:
            print(f"\n=== 현재 실행 중인 작업 ({len(tasks)}) ===")
            for i, task in enumerate(tasks, 1):
                print(f"{i}. {task.get_name()}")
        await asyncio.sleep(1)

async def main():
    print("=== 프로그램 시작 ===")
    monitor = asyncio.create_task(monitor_tasks(), name="모니터링_작업")
    try:
        result = await get_applyhome_crawl_result(
            house_type="전체",
            jiyeok="해운대",
        )
        return result
    except asyncio.CancelledError:
        print("작업이 취소되었습니다.")
        return []
    except Exception as e:
        print(f"오류 발생: {e}")
        return []
    finally:
        # 모니터링 작업 취소
        monitor.cancel()
        try:
            await asyncio.wait_for(monitor, timeout=1.0)
        except (asyncio.TimeoutError, asyncio.CancelledError):
            pass
        
        # 모든 대기 중인 작업 취소
        pending = [t for t in asyncio.all_tasks() 
                  if t is not asyncio.current_task() and not t.done()]
        
        if pending:
            print(f"\n🔄 {len(pending)}개의 대기 중인 작업을 취소하는 중...")
            for task in pending:
                task.cancel()
            
            # 완료되지 않은 작업이 완료될 때까지 기다림 (최대 2초)
            try:
                await asyncio.wait(pending, timeout=2.0)
            except (asyncio.TimeoutError, asyncio.CancelledError):
                pass
        
        print("=== 프로그램 종료 ===")

# if __name__ == "__main__":
#     try:
#         result = asyncio.run(main())
#         # 결과가 너무 길 경우를 대비해 일부만 출력
#         if isinstance(result, (list, tuple)) and len(result) > 3:
#             print("\n=== 결과 (일부) ===")
#             for i, item in enumerate(result[:3], 1):
#                 print(f"[{i}] {str(item)[:100]}...")
#             print(f"...(총 {len(result)}개 중 3개 표시)")
#         else:
#             print("\n=== 결과 ===")
#             print(result)

#     except Exception as e:
#         print(f"\n치명적 오류: {e}")
#         import traceback
#         traceback.print_exc()

    # finally:
    #     # 추가적인 정리 작업이 필요한 경우
    #     import sys
    #     sys.exit(0)  # 강제 종료

# if __name__ == "__main__":
#     # result = asyncio.run(get_applyhome_crawl_result(
#     #     house_type="전체",
#     #     jiyeok="해운대",
#     #     )
#     # )
#     # print(result)

#     result = asyncio.run(main())
#     print(result)

    

if __name__ == "__main__":
    # Smithery HTTP 배포를 위해 반드시 streamable-http transport로 실행
    # mcp.run(transport="streamable-http", host="0.0.0.0", port=8000, path="/mcp")
    mcp.run("stdio")