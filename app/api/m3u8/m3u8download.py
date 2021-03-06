import os
import re
import shutil
import threading
import requests
from django.http import HttpResponse

from django.shortcuts import render
from fake_useragent import UserAgent
from rest_framework.views import APIView

from app.models import get_uuid
from mydownloader.settings import BASE_DIR


class M3u8downloadAPIView(APIView):
    def get(self, request):
        url = request.GET['url']
        name = request.GET['name']
        currentname = re.sub('[\/:*?"<>|]', " ", name)  # 獲取標題 以window檔案命名規則 當作檔名
        file_path = self.downloadm3u8(url, currentname)
        '''轉址到video頁面'''
        return render(request, 'index.html',locals())

        '''轉址到video頁面'''
        # return render(request, 'video.html',locals())

        '''直接下載'''
        # videofile = open(file_path, 'rb')  # 讀取tslist
        # response = HttpResponse(FileWrapper(videofile), content_type='application/video')
        # response['Content-Disposition'] = 'attachment; filename="%s"' % 'video.mp4'
        # return response

    def getHeader(self):
        return {
            'User-Agent': UserAgent().random,
            'Accept': '*/*',
            'Accept-Encoding': 'gzip, deflate, sdch',
            'Accept-Language': 'zh-TW,zh;q=0.8,en-US;q=0.6,en;q=0.4',
            # 'If-Modified-Since': 'Tue, 01 Nov 2016 07:29:02 GMT'
        }

    def downloadm3u8(self, m3u8listUrl, fileName=""):
        if(fileName == ""):
            fileName = get_uuid().__str__()
        print(m3u8listUrl)
        maxexecutenum = 5
        mysession = requests.session()
        tsUrl = m3u8listUrl.split('?')[0]
        videoTag = tsUrl.split("/")[-1]
        # load_proxies_list()
        # proxy = get_random_proxies()
        # print(proxy)
        rests = mysession.get(m3u8listUrl, headers=self.getHeader())  # 獲取.ts list網址
        folder_path = str(BASE_DIR) + '//m3u8_download//' + fileName + '//'
        print(folder_path)

        upfolder_path = str(BASE_DIR) + '//static//result//'
        if os.path.exists(folder_path) == False:  # 判斷資料夾是否存在
            os.makedirs(folder_path)  # 創建資料夾

        temptsfile = open(folder_path + 'tslisttemp.txt', 'w', encoding='UTF-8')  # 將.ts list儲存成檔案
        temptsfile.write(rests.text)
        temptsfile.close()

        aryts = []  # 存放ts網址
        arytsfilename = []  # 存放ts檔案名
        count = 0
        with open(folder_path + 'tslisttemp.txt', 'r') as file:  # 讀取tslist
            lines = file.readlines()
            for line in lines:
                if line.endswith('.ts\n'):  # 判斷結為為.ts
                    count += 1
                    tsUrltmp = line.strip('\n') if line.startswith('http') else tsUrl.replace(videoTag, line.strip('\n'))
                    aryts.append(tsUrltmp)  # 字串處理變成.ts下載網址
                    name = "%05d" % count + ".ts"
                    arytsfilename.append(name)  # 檔案名列表
            file.close()
        print(aryts)
        print(arytsfilename)
        # return fileName + ".mp4"
        threads = []
        for ts, name in zip(aryts, arytsfilename):  # 下載ts列表
            print(ts,name)
            t = threading.Thread(target=self.downloadtsfile, args=[ts, name, folder_path])
            t.start()
            threads.append(t)
            print("+" + t.name)
            if len(threads) >= int(maxexecutenum):
                for thread in threads:
                    thread.join()
                    print("-" + t.name)
                threads.clear()
        for thread in threads:
            thread.join()
        threads.clear()
        self.alltscombination(folder_path, fileName, upfolder_path)  # 將所有.ts合併成mp4
        shutil.rmtree(folder_path)  # 移除下載.ts的資料夾
        # return "//result//" + fileName + ".mp4"
        return upfolder_path + fileName + ".mp4"

    def downloadtsfile(self, url, filename, folder_path=None):
        response = requests.get(url, stream=True)
        if response.status_code == 200:
            if folder_path != None:
                if os.path.exists(folder_path) == False:  # 判斷資料夾是否存在
                    os.makedirs(folder_path)  # 創建資料夾
                total_path = folder_path + filename
            else:
                total_path = filename
            if len(response.content) == int(response.headers['Content-Length']):
                with open(total_path, 'wb') as f:
                    for chunk in response.iter_content(1024):
                        f.write(chunk)
                    f.close()
        response.close()

    def alltscombination(self, folder_path, savefile_name, savefile_dir=None):
        if os.path.exists(folder_path) != False:
            os.chdir(folder_path)  # cmd切換到此資料夾
            if savefile_dir != None and os.path.exists(savefile_dir) == False:
                os.makedirs(savefile_dir)  # 創建資料夾
            savepath = savefile_name + '.mp4' if savefile_dir == None else savefile_dir + savefile_name + '.mp4'
            # shell_str = 'copy /b *.ts ' + savepath
            shell_str = 'cat *.ts > ' + savepath
            print(shell_str)
            os.system(shell_str)
            os.chdir(savefile_dir)  # 改變正在使用的目錄 防止使用中