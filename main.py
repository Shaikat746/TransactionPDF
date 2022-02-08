from fastapi import FastAPI
from PyPDF2 import PdfFileWriter, PdfFileReader
import io
import base64
import pdfkit
import requests
import pandas as pd
import datetime

from pydantic import BaseModel
from reportlab.pdfgen import canvas
import logging
import boto3
from botocore.exceptions import ClientError
import os
#import matplotlib

class Item(BaseModel):
    username: str
    password: str
    startDate: str
    endDate: str
    agentCode: int
app = FastAPI()

def dateFormat(dt):
    x = dt.split(' ')
    y1 = x[0]
    y2 = x[1]
    y11 = y1.split('-')
    y22 = y2.split(':')
    y = datetime.date(int(y11[0]), int(y11[1]), int(y11[2]))
    z = datetime.time(int(y22[0]), int(y22[1]), int(y22[2]))
    print(y1)
    return (y.strftime("%d%b  %Y") + "   " + z.strftime("%I:%M:%p"))


def getDte():
    current_time = datetime.datetime.now()
    year = current_time.year
    month = current_time.month
    day = current_time.day
    x = datetime.datetime(year, month, day)

    return x.strftime("%d%b  %Y")


def lambda_handler(username,password,startDate,endDate):
    Url = "https://developer.sandbox.stylopay.com/oauth/token";
    consumer_key_secret = "swagger-client" + ":" + "swagger-secret";
    consumer_key_secret_enc = base64.b64encode(consumer_key_secret.encode()).decode()
    headersAuth = {
        'Authorization': 'Basic ' + str(consumer_key_secret_enc),
        'xApiKey': "tDwjoMFPiL1XDYTjb8H313BWbmFlh1ve21usj7Oj",
        'Content-Type': "application/x-www-form-urlencoded"
    }

    data = {
        'username': username,
        'password': password,
        'grant_type': "password"
    }
    accessToken = requests.post(url=Url, headers=headersAuth, params=data)
    # print("Access Token is:%s", accessToken.json()['access_token'])
    token = accessToken.json()['access_token']
    urlFetchCustomer = "https://developer.sandbox.stylopay.com/NISG/api/v1/fetchCustomer"
    payloadFetchCustomer = {}
    headersFetchCustomer = {
        'x-api-key': 'tDwjoMFPiL1XDYTjb8H313BWbmFlh1ve21usj7Oj',
        'clientHasID': 'cebd2dfb-b010-48ef-b2f2-ac7e640e3a68',
        'Authorization': 'Bearer ' + token
    }
    paramFetchCustomer = {
        'order': 'DESC',
        'page': '0',
        'size': '10',
        'email': username,
        'mobile': ''
    }
    responseFetchCustomer = requests.get(url=urlFetchCustomer, headers=headersFetchCustomer, data=payloadFetchCustomer,
                                         params=paramFetchCustomer)
    items1 = responseFetchCustomer.json()
    # print(responseFetchCustomer.status_code)
    # print(items1)
    for item in items1:
        WalFetchCus = item['walletHashId']
        CusFetchCus = item['customerHashId']
        AddressFetchCustomer = item['billingAddress1'] + ", " + item['billingAddress2']
        Name = item['firstName'] + " " + item['middleName'] + " " + item['lastName']
    page = 0
    items2 = None
    items3 = []
    cus = CusFetchCus
    wal = WalFetchCus
    url11 = "https://developer.sandbox.stylopay.com/NISG/api/v1/getTransaction/"
    URL11 = url11 + cus + "/" + wal
    payload11 = {}
    headers11 = {
        'x-api-key': 'tDwjoMFPiL1XDYTjb8H313BWbmFlh1ve21usj7Oj',
        'clientHasID': 'cebd2dfb-b010-48ef-b2f2-ac7e640e3a68',
        'Authorization': 'Bearer ' + token
    }

    param11 = {
        'size': '2',
        'endDate': endDate,
        'page': '',
        'startDate': startDate
    }

    response11 = requests.request("GET", URL11, headers=headers11, data=payload11, params=param11)
    # print(response.status_code)
    # print(response.json())
    items11 = response11.json()

    url1 = "https://developer.sandbox.stylopay.com/NISG/api/v1/getTransaction/"
    URL = url1 + cus + "/" + wal
    payload = {}
    headers = {
        'x-api-key': 'tDwjoMFPiL1XDYTjb8H313BWbmFlh1ve21usj7Oj',
        'clientHasID': 'cebd2dfb-b010-48ef-b2f2-ac7e640e3a68',
        'Authorization': 'Bearer ' + token
    }

    param = {
        'size': items11["totalElements"],
        'endDate': endDate,
        'page': '',
        'startDate': startDate
    }

    response = requests.request("GET", URL, headers=headers, data=payload, params=param)
    # print(response.status_code)
    # print(response.json())
    items2 = response.json()
    if items2 != {}:
        for i in items2['content']:
            items3.append(i)
        # print(items3)
        # print(len(items3))

    amount = []
    date = []
    refID = []
    debit = []
    description = []
    balancelist = []
    comment = []

    for i in items3:
        if i['authCurrencyCode'] != None:
            amount.append("%.2f" % i["authAmount"] + " " + i['authCurrencyCode'])
        else:
            amount.append("%.2f" % i["authAmount"] + " " + i['transactionCurrencyCode'])
        if i['createdAt'] != {}:
            date.append(dateFormat(i['createdAt']))
        else:
            date.append("NA")
        if i["retrievalReferenceNumber"] != {}:
            refID.append(i["retrievalReferenceNumber"])
        else:
            refID.append("NA")

        if i["debit"]:
            debit.append("Debit")
        else:
            debit.append("Credit")
        comment.append(i["comments"])
        if i["merchantName"] != None:
            description.append(i["merchantName"])
        else:
            if i['transactionType'] == "Customer_Wallet_Debit_Fund_Transfer":
                if i["labels"] != {}:
                    description.append(
                        "Fund Transfer to: " + i["labels"]["receiverFirstName"] + " " + i["labels"]["receiverLastName"])
                else:
                    description.append("NA")
            elif i['transactionType'] == "Customer_Wallet_Credit_Fund_Transfer":
                if i["labels"] != {}:
                    description.append(
                        "Fund Received From: " + i["labels"]["senderFirstName"] + " " + i["labels"]["senderLastName"])
                else:
                    description.append("NA")
            elif i['transactionType'] == "Wallet_Refund":
                description.append(i["comments"])
            elif i['transactionType'] == "Insufficient funds|Insufficient funds":
                description.append("Insufficient funds")
            elif i['transactionType'] == "Wallet_Fund_Transfer":
                description.append("Wallet Fund Exchange")
            elif i['transactionType'] == "Customer_Wallet_Debit_Fund_Transfer":
                description.append("Fund Transfer")
            elif i['transactionType'] == "Customer_Wallet_Credit_Fund_Transfer":
                description.append("Fund Received")
            elif i['transactionType'] == "Wallet_Credit_Mode_Prefund_Cross_Currency":
                description.append("Pre-fund wallet credit")
            elif i['transactionType'] == "Wallet_Credit_Mode_Prefund":
                description.append("Pre-fund wallet credit")
            elif i['transactionType'] == {}:
                description.append("NA")

        if i["debit"]:
            if i['authCurrencyCode'] != None:
                balancelist.append("%.2f" % (i["previousBalance"] - i["authAmount"]) + " " + i['authCurrencyCode'])
            else:
                balancelist.append(
                    "%.2f" % (i["previousBalance"] - i["authAmount"]) + " " + i['transactionCurrencyCode'])
        else:
            if i['authCurrencyCode'] != None:
                balancelist.append("%.2f" % (i["previousBalance"] + i["authAmount"]) + " " + i['authCurrencyCode'])
            else:
                balancelist.append(
                    "%.2f" % (i["previousBalance"] + i["authAmount"]) + " " + i['transactionCurrencyCode'])

    print(amount)
    print(date)
    print(refID)
    print(debit)
    print(description)
    print(balancelist)
    d = {'Date/Time': date, 'Reference Id': refID, 'Description': description, 'Amount': amount, 'Type': debit,
         'Balance': balancelist}
    df = pd.DataFrame(data=d)
    print(df)
    print("jjjjjjjjjjjjjjjjjjjjjjj", len(df))
    df3 = pd.DataFrame(data=d)
    selection = ['Date/Time', 'Reference Id', 'Comments', 'Amount', 'Type', 'Balance']
    df2 = df.head(len(df)).style.set_table_styles(
        [{'selector': 'th',
          'props': [('background', 'white'),
                    ('color', 'black'),
                    ('font-family', 'verdana')]},

         {'selector': 'td',
          'props': [('font-family', 'verdana'),
                    ('padding', '11px'),
                    ('border-collapse', 'collapse')]},

         {'selector': 'tr:nth-of-type(odd)',
          'props': [('background', '#DCDCDC')]},

         {'selector': 'tr:nth-of-type(even)',
          'props': [('background', 'white')]},

         ]
    ).hide_index()
    pd.set_option('colheader_justify', 'center')  # FOR TABLE <th>
    css = ['C:\\Users\Shaikat Bhowmick\PycharmProjects\APIinvoke\python\style.css']
    html_string = '''
        <html>
          <head><title></title></head>
          <body>
          <div style="font-family:courier;" align = "right">
          <p><h4>{companyName}</h4><br>{addressLine1}<br> {addressLine2}<br> {companyMail}
         </p><br>
         <p><b>STATEMENT OF ACCOUNT</p>
          </div>

          <div style="font-weight:normal;font-family:courier;" align="left">
          <p>Statement Date:     {date}<br><br>
             Period Covered:     01 Jul 2021 to 28 Sep 2021</p><br><br>
          <p>Name :              {Name}<br><br>
             Address :           {AddressFetchCustomer}<br><br></p>
          </div>


            {table}
          </body>
          </html>
        '''
    df2.to_html('TR7.html')
    with open('TR7.html', 'w') as f:
        f.write(
            html_string.format(table=df2.to_html(), companyName='SUPREME FINTECH',
                               addressLine1='1 Burwood Place, London',
                               addressLine2='England, W2 2UT', companyMail='info@supremefintech.com', Name=Name,
                               AddressFetchCustomer=AddressFetchCustomer, date=getDte()))

    pdfkit.from_file("TR7.html", "TRansaction7.pdf")


def add_image(agentCode):
    in_pdf_file = 'TRansaction7.pdf'
    out_pdf_file = 'with_imageTRansaction7.pdf'
    agCode = agentCode
    if agCode == 101:
        img_file = 'supreme.jpg'
    if agCode == 100:
        img_file = 'favicon.png'

    packet = io.BytesIO()
    can = canvas.Canvas(packet)
    # can.drawString(10, 100, "Hello world")
    x_start = 32
    y_start = 760
    can.drawImage(img_file, x_start, y_start, width=120, preserveAspectRatio=True, mask='auto')
    can.showPage()
    can.showPage()
    can.showPage()
    can.save()

    # move to the beginning of the StringIO buffer
    packet.seek(0)

    new_pdf = PdfFileReader(packet)

    # read the existing PDF
    existing_pdf = PdfFileReader(open(in_pdf_file, "rb"))
    output = PdfFileWriter()

    for i in range(len(existing_pdf.pages)):
        page = existing_pdf.getPage(i)
        page.mergePage(new_pdf.getPage(i))
        output.addPage(page)

    outputStream = open(out_pdf_file, "wb")
    output.write(outputStream)
    outputStream.close()


def upload_file(file_name, bucket, object_name=None):
    """Upload a file to an S3 bucket

    :param file_name: File to upload
    :param bucket: Bucket to upload to
    :param object_name: S3 object name. If not specified then file_name is used
    :return: True if file was uploaded, else False
    """

    # If S3 object_name was not specified, use file_name
    if object_name is None:
        object_name = os.path.basename(file_name)

    # Upload the file
    s3_client = boto3.client('s3')
    try:
        response = s3_client.upload_file(file_name, bucket, object_name)
    except ClientError as e:
        logging.error(e)
        return False
    return True


@app.post("/test")
async def root(item:Item):
    lambda_handler(item.username,item.password,item.startDate,item.endDate)
    add_image(item.agentCode)
    if upload_file('with_imageTRansaction7.pdf', 'shaikat'):
        return {"Upload complete"}
    else:
        return {"not done"}
