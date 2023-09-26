import openpyxl as excel
import unicodedata
import re
from enum import Enum, auto
import datetime
import glob
import platform
import unicodedata


#------------------------------------
# ユーザーカスタム
#------------------------------------
#-- 選択ディレクトリを本テーブルに登録 --#
RADIO_SELECT_LIST = [
    "235_岡安実咲",
    "236_越野翔太",
    "237_鈴木理衣名",
    "238_中澤瞭斗",
    "239_永田剛暉",
    "240_根間伸幸",
    "241_星和",
    "242_松田裕也",
    "tmp1",
    "tmp2",
]

#------------------------------------
# 定数定義
#------------------------------------
LINEFEED_CODE       = '\n'

#コメントの開始位置と終了位置（単位:カラム）
POS_COMMNET_START   = 49
POS_COMMNET_END     = 78

#最大値
MAX_DEFINE_NUM          = 20        #define名
MAX_LINE_COLUMN_NUM     = 79        #1行の最大カラム

#宣言時の上部に記載するコメント
DECLARATION_DEFINE      = '/* USER DEFINE              */'
DECLARATION_STRUCTURE   = '/* STRUCTURE DEFINITION     */'
DECLARATION_EXTERNAL    = '/* EXTERNAL DEFINITION      */'
DECLARATION_TYPEDEF     = '/* TYPEDEF DEFINITION       */'      #「研修内」では未使用
DECLARATION_FUNCTION    = '/* FUNCTION PROTOTYPE       */'
DECLARATION_INTERNAL    = '/* INTERNAL DATA    */'
DECLARATION_PROCESS     = '/* PROCESS          */'

#-- ヘッダー・フッター 定型文 --#
#共通
FIXED_STR_COMMON                = '/************************************************************/'

#ファイルヘッダー
FIXED_STR_FILEHEADER_TITLE      = '/*****  FILE DESCRIPTION  ***********************************/'
FIXED_STR_FILEHEADER_FILENAME   = '^\/\*  ファイル名  ： ｈｏｔ[０-９][０-９][０-９]．ｃ                         \*\/$'
FIXED_STR_FILEHEADER_NUMBER     = '^\/\*  問題番号    ： 第[０-９]章  問題[０-９]                           \*\/$'
FIXED_STR_FILEHEADER_VERSION    = '^\/\*  ヴァージョン： [0-9].[0-9][0-9]  [0-9][0-9][0-9][0-9]/[0-9][0-9]/[0-9][0-9]  [^ ]'

#(ヘッダ用　作り悪いため要修正)
FIXED_STR_FILEHEADER_FILENAME_H = '^\/\*  ファイル名  ： ｈｏｔ[０-９][０-９][０-９]．ｈ                         \*\/$'

#関数ヘッダー
FIXED_STR_FUNCHEADER_TITLE      = '/*****  FUNCTION DESCRIPTION  *******************************/'
FIXED_STR_FUNCHEADER_FILENAME   = '^\/\*  関数名    ： ([0-9a-zA-Z _]){43}\*\/'
FIXED_STR_FUNCHEADER_CONTENTS   = '^\/\*  内  容    ： '
FIXED_STR_FUNCHEADER_RETURN     = '^\/\*  リターン値： '
FIXED_STR_FUNCHEADER_CONTINUED  = '^\/\*               '          #内容、リターンの続きの行の前半部

#ファイルフッター
FIXED_STR_FILEFOOTER_FILENAME_C   = '\/\*  FILE END： hot[0-9][0-9][0-9].c                                     \*\/'         #「:」=半角表記
FIXED_STR_FILEFOOTER_FILENAME_H   = '\/\*  FILE END： hot[0-9][0-9][0-9].h                                     \*\/'         #「:」=半角表記


#ファイルヘッダー定型文
FIXED_STR_FILEHEADER_LIST = [
    #行順に並べる
    FIXED_STR_FILEHEADER_TITLE,
    FIXED_STR_FILEHEADER_FILENAME,
    FIXED_STR_FILEHEADER_NUMBER,
    FIXED_STR_FILEHEADER_VERSION,
    FIXED_STR_COMMON,
]

#「49～78行目に入る全角文字」の数（前後に半角スペースありの場合）
#例)/* １２３４５６７８９０１２ */
STANDARD_COMMENT_MAX_NUM = 12

#行種別
class LINEKIND(Enum):
    INCLUDE         = auto()     #include
    DEFINE          = auto()     #define
    FUNC_PROTOTYPE  = auto()     #関数プロトタイプ
    FUNC_DEFINITION = auto()     #関数定義
    VARIABLE        = auto()     #変数定義
    STRUCT          = auto()     #構造体定義の先頭
    STRUCT_MEMBER   = auto()     #構造体メンバ
    PARAMETER       = auto()     #関数定義の引数
    IF_ELSEIF       = auto()     #if文、else if文
    ELSE            = auto()     #else文
    LOOP            = auto()     #while文、for文
    SWITCH          = auto()     #switch文, case文, default文
    RETURN          = auto()     #return文
    CALL_FUNC       = auto()     #関数コール
    SUBSTITUTE      = auto()     #代入処理
    OTHER           = auto()     #それ以外


#演算子の種類
OPERATER_KIND = {
    '[=!\+\-\*/%<>]=': '.=',                    #「△=」
    '[^=!\+\-\*/%<>]=[^=!\+\-\*/%<>]': '=',     #「=」のみ
    '<<': '<<',                                 #シフト演算子
    '>>': '>>',                                 #シフト演算子
    '[^>\-]>[^>=]': '>',                        #比較演算子
    '[^<]<[^<=]': '<',                          #比較演算子
    '>=': '>=',                                 #比較演算子
    '<=': '<=',                                 #比較演算子
    '\+\+': '++',                               #インクリメント
    '--': '--',                                 #デクリメント
    '\|\|': '||',                               #||
    '&&': '&&',                                 #&&
    '[^\|]\|[^\|]': '|',                        #|
    '[^&]&[^&]': '&',                           #&
    '[^\+]\+[^\+]': '+',                        #+
    '[^\-]\-[^\->]': '-',                       #-
    '[%]': '%',                                 #%
    '[^/]\*[^/]': '*',                          #*
    '[^\*]/[^\*]': '/',                         #/
    '![^=]': '!',                               #!
}

#全角文字変換テーブル
FULL_WIDTH_TABLE = {
                "a":"ａ",
                "b":"ｂ",
                "c":"ｃ",
                "d":"ｄ",
                "e":"ｅ",
                "f":"ｆ",
                "g":"ｇ",
                "h":"ｈ",
                "i":"ｉ",
                "j":"ｊ",
                "k":"ｋ",
                "l":"ｌ",
                "m":"ｍ",
                "n":"ｎ",
                "o":"ｏ",
                "p":"ｐ",
                "q":"ｑ",
                "r":"ｒ",
                "s":"ｓ",
                "t":"ｔ",
                "u":"ｕ",
                "v":"ｖ",
                "w":"ｗ",
                "x":"ｘ",
                "y":"ｙ",
                "z":"ｚ",
                "0":"０",
                "1":"１",
                "2":"２",
                "3":"３",
                "4":"４",
                "5":"５",
                "6":"６",
                "7":"７",
                "8":"８",
                "9":"９",
                "_":"＿",
                ".":"．",
                }

#空白チェック  2文字演算子
SPACE_CHECK_OPE_LIST = [
    "!=",
    "==",
    "<=",
    ">=",
    "<<",
    ">>",
    #"++",
    #"--",
    #"**",
    #"//",
    "+=",
    "-=",
    "*=",
    "/=",
    "&&",
    "||",
]

#空白チェック  2文字演算子
CONDITIONAL_OPE = [
    "!=",
    "==",
    "<=",
    ">=",
    "&&",
    "||",
]

#違反種別
VIOLATION_TYPE_FILEHEADER = '【ファイルヘッダ】'
VIOLATION_TYPE_FILEFOOTER = '【ファイルフッタ】'
VIOLATION_TYPE_FUNCHEADER = '【関数ヘッダ】'
VIOLATION_TYPE_INCLUDE = '【インクルード】'
VIOLATION_TYPE_USAGE_RESTRICTIONS = '【使用制限違反】'
VIOLATION_TYPE_NEST = '【ネストの表現】'
VIOLATION_TYPE_SENTENCE = '【文の表現】'
VIOLATION_TYPE_COMMENT = '【コメント】'
VIOLATION_TYPE_REQUIRED_COMMENT = '【必須コメント】'
VIOLATION_TYPE_DEFINE = '【Ｄｅｆｉｎｅ】'
VIOLATION_TYPE_EXTERNAL = '【Ｅｘｔｅｒｎａｌ】'
VIOLATION_TYPE_VARIABLE = '【変数宣言】'
VIOLATION_TYPE_STRUCT = '【構造体】'
VIOLATION_TYPE_PREPROCESSOR = '【プリプロセッサ】'
VIOLATION_TYPE_IDENTIFIER = '【識別子の定義】'
VIOLATION_TYPE_FUNCTION = '【関数の記述】'
VIOLATION_TYPE_IN_FUNCTION = '【関数内の記述】'
VIOLATION_TYPE_WHOLE = '【全体】'
VIOLATION_TYPE_OTHER = '【その他】'

# OS種別
OS_WINDOWS   = 0
OS_LINUX     = 1

# 「platform.system()」をコールして取得できるwindows文字列
OS_WINDOWS_STR = 'Windows'

#-------------------
# 表示メッセージ
#-------------------
# 正誤ラベル
DISPLAY_MSG_NORMAL_LABEL = '〇：'
DISPLAY_MSG_ERROR_LABEL  = '× ：'
# 正誤文字色
DISPLAY_MSG_NORMAL_COLOR = '0000FF'
DISPLAY_MSG_ERROR_COLOR  = 'FF0000'


#------------------------------------
# グローバル変数
#------------------------------------
#-- Excel --#
ExcelOutputLine         = 2                     #違反内容を出力開始行
ExcelName               = ''                    #Excelファイル名
Workbook                = excel.Workbook()      #出力対象book

#-- ファイル情報 --#
FileName            = ''               #検証中のファイル名
ReadLineNum         = 1                #判定中のライン行数
LineNum             = 0                #ファイル内行数（EOF が2行目先頭にある場合、この変数は「1」を保持する）
FirstFuncDefinition = 0                #一番先頭の関数定義行

#-- 問題 --#
ProblemNum          = ''               #問題番号

#-- チェック状態 --#
StructReadFLg           = False             #構造体チェック中（構造体定義を判定している間はTrueにする）
StructDeclarationFLg    = False             #構造体の宣言コメントチェック済みフラグ（False = 未チェック） ★ファイルが複数ある場合には、再初期化必須
FuncPrototypeReadFLg    = False             #関数プロトタイプチェック中（判定している間はTrueにする）
CallPrintfFLg           = False             #printf()コール中（コール中の行の場合はTrueにする）
CtrlFLg                 = LINEKIND.OTHER    #制御文の()中（コール中の行の場合はTrueにする）

#-- 記述位置 --#
PreDefine1stPos = 0                    #文字列１の記述位置（単位：カラム）：define用
PreDefine2ndPos = 0                    #文字列２の記述位置（単位：カラム）：define用
PreExternVarPos = 0                    #extern変数名記述位置            ：extern用
PreVar1stPos    = 0                    #文字列１の記述位置（単位：カラム）：変数用
PreMember1stPos = 0                    #文字列１の記述位置（単位：カラム）：メンバ用
PreParameterPos = 0                    #引数名の記述位置（単位：カラム）  ：引数用

#-- 出力メッセージ管理 --#
DisplayMsgManager = None

#-- 本プログラムの実行環境（OS） --#
OSKind = OS_WINDOWS


#----------------------------------
#  本プログラムの実行環境（OS）を取得
#----------------------------------
def getOSInformation():

    if platform.system() == OS_WINDOWS_STR:
        return OS_WINDOWS
    else:
        return OS_LINUX

#----------------------------------
#  path付き文字列から、ファイル名を取得
#----------------------------------
def getFileName( fileWithPath ):

    global OSKind

    # Path分解用の文字
    if OSKind == OS_WINDOWS:
        # 「./test\hot506.c」を「./test」「hot506.c」に分解
        splitStr = '\\'
    else:
        # 「./hot506.c」を「.」「hot506.c」に分解
        splitStr = '/'


    # path分解してファイル名を抽出
    tmpFile = fileWithPath.split( splitStr )
    fileName = tmpFile[1]

    return fileName


#----------------------------------
# 表示メッセージチェック
#----------------------------------
class DisplayMessageManager:

    #---------------------------------------------------
    # 問題毎のメッセージと有無判定（0：固定文字列検索, 1：正規表現検索, ２：正しい）
    #---------------------------------------------------
    FIX = 0
    REGULAR_EXPRESSION = 1
    CORRECT = 2
    
    # printfのないファイル指定時のリスト
    msg_notTarget = {'' : FIX} 

    msg_hot101 = {"Hello !!" : FIX, "My name is" : FIX, "This is my C Program." : FIX}
    msg_hot102 = {'Input number : "' : FIX, "Decimal = " : FIX, ", Hex = " : FIX}
    msg_hot103 = {'Input Number1 : "' : FIX, 'Input Number2 : "' : FIX, "%d + %d = %10d" : FIX, "%d - %d = %10d" : FIX, "%d * %d = %10d" : FIX, "%d / %d = %10d" : FIX, "%d %% %d = %10d" : FIX}
    msg_hot104 = {'Input Number1 : "' : FIX, 'Input Number2 : "' : FIX, "Number1(%d) Bigger than Number2(%d)." : FIX, "Number2(%d) Bigger than Number1(%d)." : FIX, "Number1(%d) Equal to Number2(%d)." : FIX}
    msg_hot105 = {"Program hot105 end !!" : FIX}
    msg_hot106 = {"Enter any character." : FIX, "Numeric characters = %d" : FIX}
    msg_hot107 = {"Enter any character." : FIX, "Please input a - z !!" : FIX}

    msg_hot201 = {'Input Number1 : "' : FIX, 'Input Number2 : "' : FIX, 'Input Number3 : "' : FIX, 'Maximum Number : %d' : FIX}
    msg_hot202 = {'Input Point(%d) : "' : FIX, 'Average Point  : %.1f' : FIX, 'Error : No Input Point !!' : FIX}
    msg_hot203 = {'Input number : "' : FIX, 'error ==> Input number range 2 - 100 !!' : FIX, 'The sum of 1 to %d is %d' : FIX}
    msg_hot204 = {'Input string : "' : FIX, 'Vertical string' : FIX}
    msg_hot205 = {'Input String : "' : FIX, 'String Length   : %d' : FIX, 'Original String : %s' : FIX, 'Reverse  String : %s' : FIX}
    msg_hot206 = {'Input Data(%d) : "' : FIX, 'Data No.  "' : FIX, '0....v...10....v...20....v...30....v...40....v...50' : FIX, 'Data(%d) :  "' : FIX}
    msg_hot207 = {'Input string : "' : FIX, 'Sort string  : %s' : FIX}

    msg_hot301 = {'Input String     :  "' : FIX, 'Number   String  :  %s   Input length  :  %d' : FIX, 'Alphabet String  :  %s   Input length  :  %d' : FIX, 'Another  String  :  %s   Input length  :  %d' : FIX}
    msg_hot302 = {'Enter any string.' : FIX}
    msg_hot303 = {'このプログラムは、' : FIX, '日本語モードで動作しています。' : FIX, 'Ｅｎｔｅｒキーを押して下さい。' : FIX, 'This Program is' : FIX, 'Running for English Mode.' : FIX, 'Press Enter Key, Please !!' : FIX}
    msg_hot304 = {'Input Two Numbers' : FIX, 'Max Value = %d' : FIX}
    msg_hot305 = {'Enter any character.' : FIX, 'Original  Hex     = %x' : FIX, 'Last Four Bit Off = %x' : FIX, 'Last Four Bit On  = %x' : FIX}
    msg_hot306 = {'Enter any number.' : FIX, 'Shift Bit = %d  Value = %d' : FIX}
    msg_hot307 = {'Input Number : "' : FIX, 'Hex    : 0x%X' : FIX, 'Binary : "' : FIX}
    msg_hot308 = {'Input Number %d : "' : FIX, 'error ==> Please Input Number 0 to 255.' : FIX, 'Input Numbers =' : FIX}
    msg_hot309 = {'Input Binary String : "' : FIX, 'Decimal Data : %d' : FIX, '** ERROR : Input Invalid Binary String !! **' : FIX, '** ERROR : Binary String Too Long !! **' : FIX}

    msg_hot401 = {'Input Data1     : "' : FIX, 'Input Data2     : "' : FIX, 'Input Operation : "' : FIX, 'error ==> Invalid Operation' : FIX, 'Calculate Result ( %d %c %d ) is %d' : FIX}
    msg_hot402 = {'Input Char  : "' : FIX, 'Numeric Count = %d' : FIX}
    msg_hot403 = {'Input  Number : "' : FIX, 'Input Data  =' : FIX, 'Input Count = %d' : FIX, '** Input Data Nothing !! **' : FIX}
    msg_hot404 = {'Input Data1 : "' : FIX, 'Input Data2 : "' : FIX, '** error : Cannot Divide by Zero **' : FIX, '%d %c %d = %d' : FIX}
    msg_memu_display = {'**  MENU  **' : FIX, ' 1. a + b' : FIX, ' 2. a - b' : FIX, ' 3. a * b' : FIX, ' 4. a / b' : FIX, ' 5. a %% b' : FIX, ' 6. e n d' : FIX}
    msg_select_input = {'Input Select Number : "' : FIX, '** error : Invalid Select Number **' : FIX}

    msg_hot501 = {'Key in  Number1  Number2' : FIX, 'Before  Num_Swap  Number1 = %d  Number2 = %d' : FIX, 'After   Num_Swap  Number1 = %d  Number2 = %d' : FIX}
    msg_hot502 = {'Input  String : "' : FIX, 'String Length : %d' : FIX}
    msg_hot503 = {'Input  String1 : "' : FIX, 'Input  String2 : "' : FIX, 'String Concatenate : %s' : FIX, 'Concatenate Length : %d' : FIX}
    msg_hot504 = {'Input Number Please ...' : FIX, 'Max Value = %d  Input Count = %d' : FIX, '** Error : No Input Number ...' : FIX}
    msg_hot505 = {'Sunday' : FIX, 'Monday' : FIX, 'Tuesday' : FIX, 'Wednesday' : FIX, 'Thursday' : FIX, 'Friday' : FIX, 'Saturday' : FIX, 'Usage : %s Number(0-6)' : FIX}
    msg_hot506 = {'Usage : %s string1 string2 string3 ...' : FIX}

    msg_hot601 = {'Display Data is Nothing !!' : FIX, '** Error : No Input Data' : FIX, 'Input Data ? (y/n)  :  "' : FIX, 'Name : "' : FIX, 'Tel  : "' : FIX, 'Age  : "' : FIX, '[^ ]    \*\*\*\* Selected Members \*\*\*\*' : REGULAR_EXPRESSION, 'Name              Tel           Age' : FIX}
    msg_hot602 = {'Select  Sort  Key !!' : FIX, '1. Number' : FIX, '2. Name' : FIX, '3. Age' : FIX, 'Please Input : "' : FIX, 'Number    Name      Age' : FIX, '-------------------------' : FIX}
    
    # テンプレート
    msg_hotxxx = {'AAAA' : FIX, 'AAAA' : FIX, 'AAAA' : FIX, 'AAAA' : FIX}


    #-------------------------------------
    # ファイル名と表示メッセージデータ紐づけ
    #-------------------------------------
    linked_file = {
        # HOTC1
        "hot101.c": msg_hot101,
        "hot102.c": msg_hot102,
        "hot103.c": msg_hot103,
        "hot104.c": msg_hot104,
        "hot105.c": msg_hot105,
        "hot106.c": msg_hot106,
        "hot107.c": msg_hot107,

        # HOTC2
        "hot201.c": msg_hot201,
        "hot202.c": msg_hot202,
        "hot203.c": msg_hot203,
        "hot204.c": msg_hot204,
        "hot205.c": msg_hot205,
        "hot206.c": msg_hot206,
        "hot207.c": msg_hot207,

        # HOTC3
        "hot301.c": msg_hot301,
        "hot302.c": msg_hot302,
        "hot303.c": msg_hot303,
        "hot304.c": msg_hot304,
        "hot305.c": msg_hot305,
        "hot306.c": msg_hot306,
        "hot307.c": msg_hot307,
        "hot308.c": msg_hot308,
        "hot309.c": msg_hot309,

        # HOTC4
        "hot401.c": msg_hot401,
        "hot402.c": msg_hot402,
        "hot403.c": msg_hot403,
        "hot404.c": msg_hot404,
        "memu_display.c": msg_memu_display,
        "select_input.c": msg_select_input,

        # HOTC5
        "hot501.c": msg_hot501,
        "hot502.c": msg_hot502,
        "hot503.c": msg_hot503,
        "hot504.c": msg_hot504,
        "hot505.c": msg_hot505,

        # HOTC6
        "hot601.c": msg_hot601,
        "hot602.c": msg_hot602,
    }

    #-------------------------------------
    # コンストラクタ
    #-------------------------------------
    def __init__(self, fileName):
        # ファイル名をキーあり
        if fileName in DisplayMessageManager.linked_file:
            # ファイル名をキーとして、対象問題の表示メッセージリストを保持
            self.list = DisplayMessageManager.linked_file[fileName]

        else:
            # 指定ファイル名をキーとするリストがなければ、なし用のリストを保持
            self.list = DisplayMessageManager.msg_notTarget

        # 対象問題の表示メッセージリスト
        self.msgListMap = self.list

    #----------------
    # 照合
    #----------------
    def collationMessage(self, line):

        # 対象問題の表示メッセージ分繰り返し
        for msg in self.msgListMap:

            # 既にあることが確認できている表示メッセージは検証外
            state = self.msgListMap[msg]
            if state == DisplayMessageManager.CORRECT :
                continue

            # 固定文字列で検証
            elif state == DisplayMessageManager.FIX :
                ret = msg in line

            # 正規表現で検証
            else :
                ret = ( re.search(msg, line) != None )

            # 検証対象のライン上にあれば、ステータスを更新
            if ret == True:
                # 実装中にあれば、表示メッセージを正常に更新
                self.msgListMap[msg] = DisplayMessageManager.CORRECT

    #------------------------------------
    # 問題に対応する表示メッセージリストを取得
    #------------------------------------
    def getMessageListMap(self):
        return self.msgListMap



#----------------------------------
#　ウインドウを開く
#----------------------------------
class OpenWindow():
    def __init__(self):

        #----------------------------------------------------------
        # ！関数内のimportは非推奨！
        # 　今回はAWS環境にパッケージをインストールする手間を省く目的で
        # 　ここに実装
        #----------------------------------------------------------
        import tkinter as tk
        from tkinter import messagebox as mbox
        #----------------------------------------------------------
        # ！関数内のimportは非推奨！
        #----------------------------------------------------------


        #-- 試験用
        #self.input = 'test'
        #return
        #--

        #入力フォルダ
        self.input = ''

        #ウインドウ生成
        self.root = tk.Tk()
        self.root.title("フォルダの指定")
        self.root.geometry('500x600')

        #ラベルを作成
        label = tk.Label(self.root,
                         text='チェックしたいファイル名のあるフォルダ名を入力してください')
        label.place(x=20, y=20)

        #テキストボックスを作成
        self.text = tk.Entry(width=50)
        self.text.place(x=20, y=70)

        # ラジオボタン
        # チェック有無変数
        self.radioVar = tk.IntVar()
        # value=0のラジオボタンにチェックを入れる
        self.radioVar.set(0)

        #ラジオボタン生成
        yValue = 100
        for i, dirName in enumerate(RADIO_SELECT_LIST):
            rdo = tk.Radiobutton(self.root, value=i, variable=self.radioVar, text=dirName)
            rdo.place(x=20, y=yValue)

            yValue = yValue + 20

        #ボタン
        yValue = yValue + 20
        button = tk.Button(self.root,
                           text = 'OK',
                           command=self.quit)
        button.place(x=20, y=yValue)

        #Enterでも押せるように
        button.bind("<Return>", lambda event:self.quit())

        self.root.mainloop()

    #終了処理
    def quit(self):
        #入力情報の取得
        self.input = self.text.get()

        #テキストフォームに入力がないなら、ラジオボタンの情報参照
        if self.input == "":
            select = self.radioVar.get()

            self.input = RADIO_SELECT_LIST[select]

        print(self.input)

        #閉じる
        self.root.destroy()

#----------------------------------
#　エクセル生成
#----------------------------------
def createExcel( folder ):

    #フォルダにパス付与
    passFolder = "./" + folder + "/"

    #現在日時
    dt_now = datetime.datetime.now()
    str    = dt_now.strftime('%Y%m%d_%H時%M分%S秒')

    global ExcelName
    global Workbook
    #global Worksheet

    #新規作成(同じファイルが既にある場合は、新規で上書きされる)
    ExcelName = passFolder + str + ".xlsx"

    #Workbook  = excel.Workbook()
    Worksheet = Workbook.active

    Worksheet["A1"] = "ファイル名"
    Worksheet["B1"] = "違反行"
    Worksheet["C1"] = "種別"
    Worksheet["D1"] = "内容"
    Worksheet["E1"] = "備考"

    Workbook.save(ExcelName)

    return

#----------------------------------
# 検証対象のファイル書き込み
#----------------------------------
def writeVerifyFile( file ):

    #-----------------
    # OS判定
    #-----------------
    # Windowsでなければ何もしない
    global OSKind
    if OSKind != OS_WINDOWS:
        return

    #-----------------
    # Excelに出力
    #-----------------
    #Excel情報
    global ExcelName
    global Workbook
    global ExcelOutputLine

    Worksheet = Workbook.active

    #書き込みセル
    cell = 'A' + str(ExcelOutputLine)

    #ファイル名を出力
    Worksheet[cell] = file

    #保存
    Workbook.save(ExcelName)

    return


#----------------------------------
# 違反内容の書き込み
#----------------------------------
def writeViolation( outputKind, outputContents, outputNote ):

    #--------------------------------
    # 違反情報の出力形式をOSで切り分け
    #--------------------------------
    global OSKind
    if OSKind == OS_WINDOWS:
        # excelに出力
        outputViolationToExcel( outputKind, outputContents, outputNote )
    else:
        # コンソールに出力
        outputViolationToConsole( outputKind, outputContents, outputNote )


#----------------------------------
# 違反内容の書き込み：excel出力
#----------------------------------
def outputViolationToExcel( outputKind, outputContents, outputNote ):

    #------------------------
    # 判定中の子ライン行数
    #------------------------
    global ReadLineNum
    if ReadLineNum == 0:
        # 0行目なら、行不明とする
        outputLine = '？'
    else:
        outputLine = str(ReadLineNum) + '行目'

    #Excel情報
    global ExcelName
    global Workbook
    global ExcelOutputLine

    Worksheet = Workbook.active

    #書き込みセル
    cellLine     = 'B' + str(ExcelOutputLine)
    cellKind     = 'C' + str(ExcelOutputLine)
    cellContents = 'D' + str(ExcelOutputLine)
    cellNote     = 'E' + str(ExcelOutputLine)

    Worksheet[cellLine]     = outputLine
    Worksheet[cellKind]     = outputKind
    Worksheet[cellContents] = outputContents
    Worksheet[cellNote]     = outputNote

    Workbook.save(ExcelName)

    #書き込み行を更新
    ExcelOutputLine = ExcelOutputLine + 1

    return

#----------------------------------
# 違反内容の書き込み：コンソール出力
#----------------------------------
def outputViolationToConsole( outputKind, outputContents, outputNote ):

    #------------------------
    # 判定中の子ライン行数
    #------------------------
    global ReadLineNum
    if ReadLineNum == 0:
        # 0行目なら、行不明とする
        outputLine = '？'
    else:
        # 1行目以降なら、3桁0埋め
        outputLine = str(ReadLineNum).zfill(3) + ':'

    #------------------------
    # 出力フォーマット調整
    #------------------------
    # 違反種別を左寄せにする
    outputKindStr = outputKind.ljust(10, '　')

    # コンソール上へ出力
    print( outputLine + outputKindStr + ' ' + outputContents + ' ' + outputNote)


#----------------------------------
# 誤記のある表示メッセージを書き込み
#----------------------------------
def writeViolationDisplayMessage():

    #------------
    # Excel情報
    #------------
    global ExcelName
    global Workbook
    global ExcelOutputLine

    Worksheet = Workbook.active

    #--------------------
    # 表示メッセージ管理
    #--------------------
    global DisplayMsgManager
    msgListMap = DisplayMsgManager.getMessageListMap()

    #==============================
    # 誤りのある表示メッセージを出力
    #==============================
    #---------------
    # エラータイトル
    #---------------
    ExcelOutputLine = ExcelOutputLine + 1
    cellErrorMessage = 'B' + str(ExcelOutputLine)
    Worksheet[cellErrorMessage] = "'====表示メッセージの正誤===="

    # 書き込み行を更新
    ExcelOutputLine = ExcelOutputLine + 1

    print('====表示メッセージの正誤====')

    #-----------------------
    # 誤りのある表示メッセージ
    #-----------------------
    # 対象問題の表示メッセージ分繰り返し
    for msg in msgListMap:

        # ---------------------------------------
        # 表示メッセージ検証対象なしなら何もしない
        # ---------------------------------------
        if msg == '':
            break

        # --------------
        # 正誤で可変の値
        # --------------
        # ラベル
        label = ""
        # 文字色
        textColor = ""

        state = msgListMap[msg]
        if state == DisplayMessageManager.CORRECT :
            label = DISPLAY_MSG_NORMAL_LABEL
            textColor = DISPLAY_MSG_NORMAL_COLOR
        else:
            label = DISPLAY_MSG_ERROR_LABEL
            textColor = DISPLAY_MSG_ERROR_COLOR

        # -----------------
        # 出力文の可読性向上
        # -----------------
        # 正規表現で検証したメッセージは、出力した時わかりにくいため、「\」は削除
        if state == DisplayMessageManager.REGULAR_EXPRESSION :
            msg = msg.replace( '\\', '' )

        # 検証した表示メッセージの先頭にラべルを付与
        msg = label + msg

        #------------------------------
        # 誤りのある表示メッセージを出力
        #------------------------------
        cellErrorMessage = 'B' + str(ExcelOutputLine)
        Worksheet[cellErrorMessage] = msg

        print(msg)

        # 文字色設定
        Worksheet[cellErrorMessage].font = excel.styles.fonts.Font(color=textColor)

        # 書き込み行を更新
        ExcelOutputLine = ExcelOutputLine + 1

    # 保存
    Workbook.save(ExcelName)

    # 書き込み行を更新
    ExcelOutputLine = ExcelOutputLine + 1

    return

#----------------------------------
# 指定行の文字数を返す
# ※ 2バイト文字は、2文字とする
#----------------------------------
def countLine(line):
    #カウンタ
    counter = 0

    for char in line:
        j = unicodedata.east_asian_width(char)
        if 'F' == j:
            counter = counter + 2
        elif 'W' == j:
            counter = counter + 2
        elif 'A' == j:
            counter = counter + 2
        elif 'H' == j:
            counter = counter + 1
        elif 'Na' == j:
            counter = counter + 1
        else:
            counter = counter + 1

    return counter

#----------------------------------
# 指定行内にある「2バイト文字」の数を算出する
#----------------------------------
def count2ByteChar(line):
    #2バイト文字数
    counter = 0

    for char in line:
        j = unicodedata.east_asian_width(char)

        #2バイト文字ならカウントアップ
        if 'F' == j or 'W' == j or 'A' == j :
            counter = counter + 1

    return counter

#----------------------------------
# ヘッダー内で使用する可能性のある
# 半角文字があるか
#----------------------------------
def isHeaderHalfSize(line):

    ret = re.search('[a-z0-9\.]', line)
    if ret == None:
        #半角文字なし
        return False
    else:
        #半角文字あり
        return True

#----------------------------------
# ヘッダー内で使用する可能性のある
# 全角文字があるか
#----------------------------------
def isHeaderFullSize(line):

    ret = re.search('[０-９．／]', line)
    if ret == None:
        #全角文字なし
        return False
    else:
        #全角文字あり
        return True

#----------------------------------
# ファイルヘッダのチェック
#----------------------------------
def checkFileHeader(line):

    #フォーマットチェック
    checkFileHeaderFormat(line)

    #ファイル名との整合性チェック
    checkFileHeaderInfo(line)

#----------------------------------
# ファイルヘッダのチェック
#----------------------------------
def checkFileHeaderFormat(line):

    #判定中のライン行目
    global ReadLineNum
    #定型文リスト
    global FIXED_STR_FILEHEADER_LIST
    #ファイル名
    global FileName

    #6行目以降は、判定対象外
    if ReadLineNum > 5:
        return

    #チェック対象の定型文を取得
    frontStr = FIXED_STR_FILEHEADER_LIST[ReadLineNum - 1]

    #1行目と5行目
    if (ReadLineNum == 1) or (ReadLineNum == 5):
        if line != frontStr:
            #一致しないなら、違反
            #print('【ファイルヘッダー】フォーマット誤り')
            writeViolation( VIOLATION_TYPE_FILEHEADER, 'フォーマット誤り', '')

        return

    #2行目
    if ReadLineNum == 2:

        #-- 定型文チェック --#

        #hot~.cの場合
        if ('hot' in FileName) and ('.c' in FileName):
            ret = re.search(frontStr, line)

        #hot~.hの場合
        elif ('hot' in FileName) and ('.h' in FileName):
            ret = re.search(FIXED_STR_FILEHEADER_FILENAME_H, line)

        #hot以外
        else:
            #hot直前までのフォーマットをチェック
            ret = re.search('^\/\*  ファイル名  ： ', line)

        if ret == None:
            #一致しないなら、違反
            #print('【ファイルヘッダー】フォーマット誤り')
            writeViolation( VIOLATION_TYPE_FILEHEADER, 'フォーマット誤り', '')

    #2行目~4行目
    if (ReadLineNum >= 3) and (ReadLineNum <= 4):

        #-- 定型文チェック --#
        ret = re.search(frontStr, line)
        if ret == None:
            #一致しないなら、違反
            #print('【ファイルヘッダー】フォーマット誤り')
            writeViolation( VIOLATION_TYPE_FILEHEADER, 'フォーマット誤り', '')

    #4行目のみ
    if ReadLineNum == 4:
        #62文字か
        if not check62Column(line):
            #print('【ファイルヘッダー】62カラム違反')
            writeViolation( VIOLATION_TYPE_FILEHEADER, '62カラム違反', '')

#----------------------------------
# ファイルヘッダの情報チェック
# ・ファイル名の記載が、ファイル名と一致しているか
# ・章番号と問題番号が、ファイル名と一致しているか
#----------------------------------
def checkFileHeaderInfo(line):

    global FileName

    #ファイル名内の「hotxxx」文字数を取得
    '''
    if '_'  in FileName:
        #「_」あり
        tmp = FileName.split('_')

    else:
        #「_」なし
        tmp = FileName.split('.')
    '''

    #全角文字に変換
    transTable     = str.maketrans(FULL_WIDTH_TABLE)
    upper_fileName = FileName.translate(transTable)

    #-- ファイル名の記載が、ファイル名と一致しているか --#
    #「ファイル名～」
    if ReadLineNum == 2:

        #「ｈｏｔ６０１．ｃ」(例)を作成
        #inStr = upper_fileName + '．ｃ'
        inStr = upper_fileName

        #ファイル名と一致しないなら、違反
        if inStr not in line:
            #print(inStr)
            #print('【ファイルヘッダー】ファイル名の記載が、実際のファイル名と不一致')
            writeViolation( VIOLATION_TYPE_FILEHEADER, 'ファイル名の記載が、実際のファイル名と不一致', '')

    #-- 章番号と問題番号が、ファイル名と一致しているか --#
    elif ReadLineNum == 3:

        if 'hot' not in FileName:
            #print('【ファイルヘッダー】章番号・問題番号の検証をスルー（目視で確認）')
            writeViolation( VIOLATION_TYPE_FILEHEADER, '章番号・問題番号の検証をスルー', '本ファイルは黙視での確認をお願いします')

            return


        #「第６章  問題１」(例)を作成
        inStr = '第' + upper_fileName[3] + '章  問題' + upper_fileName[5]

        #ファイル名と一致しないなら、違反
        if inStr not in line:
            #print('【ファイルヘッダー】章番号or問題番号が、実際のファイル名と不一致')
            writeViolation( VIOLATION_TYPE_FILEHEADER, '章番号or問題番号が、実際のファイル名と不一致', '')

    return

#----------------------------------
# ヘッダーカラムチェック
#----------------------------------
def check62Column( line ):
    #-- 文末のカラム位置 --#
    count = countLine( line )

    if count != 62:
        #62文字ではない
        return False

    else:
        return True


#----------------------------------
# ファイルフッターのチェック
#----------------------------------
def checkFileFooter( line ):

    #フォーマットチェック
    checkFileFooterFormat(line)

    #ファイル名との整合性チェック
    checkFileFooterInfo(line)

#----------------------------------
# ファイルフッターのチェック
#----------------------------------
def checkFileFooterFormat( line ):

    #ファイル内行数（EOF が2行目先頭にある場合、この変数は「1」を保持する）
    global LineNum
    #判定中のライン行目
    global ReadLineNum
    #ファイル名
    global FileName

    #最後から2行目より上の行は、判定対象外
    if ReadLineNum < (LineNum - 2):
        return

    #最後から2行目 or 最終行
    if (ReadLineNum == (LineNum - 2)) or (ReadLineNum == LineNum):
        if line != FIXED_STR_COMMON:
            #一致しないなら、違反
            #print('【ファイルフッター】フォーマット誤り')
            writeViolation( VIOLATION_TYPE_FILEFOOTER, 'フォーマット誤り', '')

    #最後から1行目
    elif ReadLineNum == (LineNum - 1):
        #-- 定型文チェック --#

        #hot~の場合
        if ('hot' in line) and ('.c' in line):
            ret = re.search(FIXED_STR_FILEFOOTER_FILENAME_C, line)

        elif ('hot' in line) and ('.h' in line):
            ret = re.search(FIXED_STR_FILEFOOTER_FILENAME_H, line)

        #hot以外
        else:
            #hot直前までのフォーマットに、ファイル名を追加して検証
            ret = re.search('\/\*  FILE END： ' + FileName, line)

        if ret == None:
            #一致しないなら、違反
            #print('【ファイルフッター】フォーマット誤り')
            writeViolation( VIOLATION_TYPE_FILEFOOTER, 'フォーマット誤り', '')

    return


#----------------------------------
# ファイルフッタの情報チェック
# ・ファイル名の記載が、ファイル名と一致しているか
#----------------------------------
def checkFileFooterInfo(line):

    global FileName
    if '.'  in FileName:
        #「.」あり
        tmp = FileName.split('.')

    #拡張子よりも前の文字列
    hot = tmp[0]

    #hot の文字列を含んでいれば
    if 'hot' in hot:
        #hotxxx を保持する
        global ProblemNum
        ProblemNum = hot

    #-- ファイル名の記載が、ファイル名と一致しているか --#
    #「フFILE END」の行
    if ReadLineNum == (LineNum - 1):

        #ファイル名と一致しないなら、違反
        if FileName not in line:
            #print('【ファイルフッタ】ファイル名の記載が、実際のファイル名と不一致')
            writeViolation( VIOLATION_TYPE_FILEFOOTER, 'ファイル名の記載が、実際のファイル名と不一致', '')

    return


#----------------------------------
# common.hチェック
#　・""で囲まれているか
#　・不要なパスを記載していないか
#----------------------------------
def checkCommonH(line, lineKind):

    #include文でないなら終了
    if lineKind != LINEKIND.INCLUDE:
        return

    #common.h でないなら終了
    if "common.h" not in line:
        return

    #<>でインクルード
    if '<common.h>' in line:
        #print('【インクルード】インクルード方法誤り("")')
        writeViolation( VIOLATION_TYPE_INCLUDE, 'インクルード方法誤り("")', '')

    #パスあり
    if '/common.h' in line:
        #print('【インクルード】インクルード方法誤り(パスあり)')
        writeViolation( VIOLATION_TYPE_INCLUDE, 'インクルード方法誤り(パスあり)', '')

    return

#----------------------------------
# EOFチェック
# (行頭にEOFがあるか)
#----------------------------------
def checkEOF(line):

    #最終行に改行コードがない（改行コードなしだと、62文字になる）
    length = len(line)
    if length == 62:
        #print('【その他】EOFはファイル行頭にない')
        writeViolation( VIOLATION_TYPE_OTHER, 'EOFはファイル行頭にない', '')

    return

#--------------------------
# 検証：ヘッダ類
# ・ファイルヘッダ
# ・関数ヘッダ
# ・ファイルフッタ
#--------------------------
def verifyHeader( line, preLine, lineKind ):

    #ファイルヘッダのチェック
    checkFileHeader(line)

    #関数ヘッダのチェック
    #(別個所で実施)

    #ファイルフッタのチェック
    checkFileFooter(line)

    #common.hチェック
    checkCommonH(line, lineKind)

#------------------------------------------
# 文の末尾に余計な半角スペースがないか
#------------------------------------------
def checkUnnecessarySpace( line ):

    #文字数を取得
    charNum = len(line)

    if charNum == 0:
        #空行
        return

    #-- ある行がすべて空白か --#

    #空白数
    spaceNum = line.count(' ')
    if spaceNum == len(line):
        #空白数と行の文字数が一致
        #print('【全体】空白のみの行あり')
        writeViolation( VIOLATION_TYPE_WHOLE, '空白のみの行あり', '')
        return

    #-- 文の末尾に空白があるか --#

    #文末の文字を取得
    lastChar = line[charNum - 1]

    #文末が半角スペースなら
    if lastChar == ' ':
        #違反
        #print('【全体】文末に余計な半角スペースあり')
        writeViolation( VIOLATION_TYPE_WHOLE, '文末に余計な半角スペースあり', '')

    return

#------------------------------------------
# 使用禁止の文字がないかチェックする
#   ・全角スペース、半角カタカナ、水平タブ
#   ・goto文
#   ・末尾の半角スペース
#------------------------------------------
def checkProhibition( line ):

    #末尾の半角スペース
    checkUnnecessarySpace( line )

    #全角スペース
    ret = re.search('\u73000', line)
    if ret != None:
        #print('【使用制限違反】全角スペースあり')
        writeViolation( VIOLATION_TYPE_USAGE_RESTRICTIONS, '全角スペースあり', '')

    #半角カタカナ
    ret = re.search('[ｱｲｳｴｵｶｷｸｹｺｻｼｽｾｿﾀﾁﾂﾃﾄﾅﾆﾇﾈﾉﾊｲﾌﾍﾎﾏﾐﾑﾒﾓﾗﾘﾙﾚﾛﾔﾕﾖﾜｦﾝｯｧｨｩｪｫｬｭｮ]', line)
    if ret != None:
        #print('【使用制限違反】半角カタカナあり')
        writeViolation( VIOLATION_TYPE_USAGE_RESTRICTIONS, '半角カタカナあり', '')

    #水平タブ
    ret = re.search('\t', line)
    if ret != None:
        #print('【使用制限違反】水平タブあり')
        writeViolation( VIOLATION_TYPE_USAGE_RESTRICTIONS, '水平タブあり', '')

    #goto文
    if ' goto ' in line:
        #print('【使用制限違反】gotoあり')
        writeViolation( VIOLATION_TYPE_USAGE_RESTRICTIONS, 'gotoあり', '')

    return

#------------------------------------------
# カラムが4つずつとなっているか
#------------------------------------------
def checkColumn4Each( line ):

    #一番初めの「半角スペース以外」の文字位置を検索
    #(実質、前方の半角スペースの数になる)
    ret = re.search('[^ ]', line)
    if ret == None:
        #フェールセーフ
        spaceNum = 0
    else:
        spaceNum = ret.start()

    #print(spaceNum)

    #4の倍数でなければ、カラムエラー
    if (spaceNum % 4) != 0:
        #print('【ネストの表現】4カラム単位ずれ')
        writeViolation( VIOLATION_TYPE_NEST, '4カラム単位ずれ', '')

#------------------------------------------
# 行に2文以上の記載がないかをチェックする上で、
# 判定除外の文かを判定
#  【判定除外文】
#  判定対象行がfor文
#  判定対象行がfor文の続き
#------------------------------------------
def checkTwoProcessExclusion( line, preLine ):

    #判定対象行がfor文
    isFor = re.search(' for | for\(', line)
    if isFor != None:
        #判定対象外
        return True

    #-- 判定対象行がfor文の続きかどうか --#

    #上の行がfor文か
    isFor = re.search(' for | for\(', preLine)

    #上の行に「)」があるか
    isClose = re.search('\)', preLine)

    #for分だが「)」がないなら、for文が行をまたいでいる
    if ( isFor ) and ( not isClose ):
        #判定対象外
        return True

    return False


#------------------------------------------
# 行に2文以上の記載がないかをチェック
# 【判定方法】
#  ・1行に「;」が2つ以上ないか
#  ・「;」の横に制御文がないか
#     例) printf( ~ ); if( ~ )
#
#   ※ 以下のケースは別個所で検証しているため、検証対象外
#      if( ~ ) { ~~~ }
#------------------------------------------
def checkTwoProcess( line, preLine ):

    #判定対象外かチェック
    ret = checkTwoProcessExclusion( line, preLine )
    if ret:
        return

    #「;」2つ以上ないか
    splitList = line.split(';')
    num = len( splitList )

    #「;」2つ以上あると、分割した場合、3以上に別れる
    if num >= 3:
        #print('【ネストの表現】1行に2文以上あり')
        writeViolation( VIOLATION_TYPE_NEST, '1行に2文以上あり', '「if文」「for文」「出力メッセージ」なら問題なし')
        return

    #-- 「;」の後にコメントがあれば、「;」と「/*」の間に「半角スペース」だけしかないか
    #-- 「;」の後にコメントがなければ、「;」の後に何もないか

    #制御文のみの文
    # 例）if( ~ )
    if num == 1:
        #検証対象外
        return

    #「;」より先の文字列
    str = splitList[1]

    #コメントの有無
    if '/*' in line:
        #コメントあり

        #「/*」で分割
        commentSplit = str.split('/*')

        #「;」と「/*」の間の文字列
        checkStr = commentSplit[0]

    else:
        #コメントなし

        #検証対象の範囲は、「;」より先の文字列
        checkStr = str

    #英字があれば違反
    ret = re.search('[a-z]', checkStr)
    if ret != None:
        #print('【ネストの表現】1行に2文以上あり')
        writeViolation( VIOLATION_TYPE_NEST, '1行に2文以上あり', '「if文」「for文」「出力メッセージ」なら問題なし')

    return


#------------------------------------------
# ネストの表現のチェック
# ・段落が4カラムずつ
# ・1行に2文以上の記載がないか
#------------------------------------------
def checkNestExpression( line, preLine ):

    #カラム開始位置チェック(4カラムずつ)
    checkColumn4Each( line )

    #1行に2文以上の記載チェック
    checkTwoProcess( line, preLine )

#------------------------------------------
# ネストの表現のチェック
# ・段落が4カラムずつ
# ・1行に2文以上の記載がないか
#------------------------------------------
def checkMaxColumn( line ):

    #文字数取得
    count = countLine( line )

    #79文字を超えていれば、違反
    if count > MAX_LINE_COLUMN_NUM:
        #print('【文の表現】79文字オーバー')
        writeViolation( VIOLATION_TYPE_SENTENCE, '79文字オーバー', '')

    return

#------------------------------------------
# 空白が
#------------------------------------------
def checkControlStatementFOrmat( line ):

    pass

#------------------------------------------
# 「(」の前をチェック
# ・True
#　　「(」の前に空白が1つだけあり
# ・False
#　　上記以外
#------------------------------------------
def checkFrontSpaceBrackets( preStr ):

    ret = re.search('[^ ] $', preStr)
    if ret == None:
        #「(」の前が空白ではない or 最後の文字の空白が連続している
        return False

    else:
        #「(」の前が、空白1つだけ
        return True

#------------------------------------------
# 指定された文字の直前にある空白の数を取得
#   第3引数：「指定した文字」に関して、行内の何番目の文字を
#   　　　　　判定対象とするか
#   　　　　　※1文字目  = 0
#   　　　　　※最後指定 = 0xFF
#------------------------------------------
def getFrontSpace( word, line, num ):

    #指定文字がなければ
    if word not in line:
        return 0xFF

    #指定文字で分割
    str = line.split(word)

    #判定対象は最後の文字
    if num == 0xFF:
        index = len( str ) - 2
    else:
        index = num

    #判定対象の文字列
    checkStr = str[ index ]
    length = len(checkStr)

    #カウント
    count = 0
    for i in reversed( range( 0, length ) ):
        if checkStr[i] == ' ':
            #空白あれば、加算
            count = count + 1
        else:
            #空白以外が見つかれば、カウント終了
            break

    return count


#------------------------------------------
# 指定された文字の直前にある空白の数を取得
#   第3引数：「指定した文字」に関して、行内の何番目の文字を
#   　　　　　判定対象とするか
#   　　　　　※1文字目 = 0
#------------------------------------------
def getRearSpace( word, line, num ):

    #指定文字がなければ
    if word not in line:
        return 0xFF

    #指定文字で分割
    splitStr = line.split(word)

    #判定対象の文字列
    checkStr = splitStr[1 + num]
    length = len(checkStr)

    #カウント
    count = 0
    for i in  range( 0, length ):
        if checkStr[i] == ' ':
            #空白あれば、加算
            count = count + 1
        else:
            #空白以外が見つかれば、カウント終了
            break

    return count

#------------------------------------------
# 指定された文字の左と右に、特定の記号があるかチェック
#   第3引数：「指定した文字」に関して、行内の何番目の文字を
#   　　　　　判定対象とするか
#   　　　　　※1文字目  = 0
#   　　　　　※最後指定 = 0xFF
#  True  ： 特定の記号あり
#  False ： 特定の記号なし
#------------------------------------------
def checkExclusionChar( word, line, num ):

    #指定文字で分割
    splitStr = line.split(word)

    #判定対象は最後の文字
    if num == 0xFF:
        index = len( splitStr ) - 2
    else:
        index = num

    #-- 左側判定 --#
    #判定対象の文字列
    checkStr = splitStr[ index ]
    length   = len(checkStr)

    if checkStr == '':
        return False

    #特定の記号であれば、
    ret = re.search('[=<>!\-]', checkStr[length - 1])
    if ret:
        return True

    #-- 右側判定 --#
    '''
    #判定対象の文字列
    checkStr = splitStr[ index ]
    length   = len(checkStr)

    #判定対象文字のすぐ右が、特定の記号か
    ret = re.search('=<>!\-', checkStr[length - 1])
    if ret:
        return True
    '''

    #判定対象の文字列
    checkStr = splitStr[1 + num]

    if checkStr == '':
        return False

    #判定対象文字のすぐ右が、特定の記号か
    ret = re.search('[=<>]', checkStr[0])
    if ret:
        return True

    #条件に該当しなければ、該当なし
    return False

#------------------------------------------
# 指定された文字が、コメント内のものか、「""」内のものかを判定する
#  True  ： コメント内or「""」内
#  False ： 内ではない
#------------------------------------------
def checkInComment( word, line, num ):

    #指定文字で分割
    splitStr = line.split(word)

    #判定対象は最後の文字
    if num == 0xFF:
        index = len( splitStr ) - 2
    else:
        index = num

    #判定範囲の文字列を生成
    #(判定範囲 = 指定文字の左側)
    checkStr = ''
    for i in range( 0, index + 1 ):
        checkStr += splitStr[i]

    #「/*」あるなら
    if '/*' in checkStr:
        ##print('★コメント内★')
        return True

    #「"」が1つだけなら
    if checkStr.count('"') == 1:
        ##print('★”内★')
        return True

    return False

#------------------------------------------
# ライン種別に対応する文字列を取得
#------------------------------------------
def getLineKindStr( lineKind ):

    if lineKind  == LINEKIND.INCLUDE:
        str = 'include文'
    elif lineKind  == LINEKIND.DEFINE:
        str = 'define定義'
    elif lineKind  == LINEKIND.FUNC_PROTOTYPE:
        str = '関数プロトタイプ'
    elif lineKind  == LINEKIND.FUNC_DEFINITION:
        str = '関数定義'
    elif lineKind  == LINEKIND.VARIABLE:
        str = '変数宣言'
    elif lineKind  == LINEKIND.STRUCT:
        str = '構造体宣言'
    elif lineKind  == LINEKIND.STRUCT_MEMBER:
        str = '構造体メンバ'
    elif lineKind  == LINEKIND.PARAMETER:
        str = '引数'
    elif lineKind  == LINEKIND.IF_ELSEIF:
        str = 'if文'
    elif lineKind  == LINEKIND.ELSE:
        str = 'else文'
    elif lineKind  == LINEKIND.LOOP:
        str = 'ループ文'
    elif lineKind  == LINEKIND.SWITCH:
        str = 'switch文'
    elif lineKind  == LINEKIND.CALL_FUNC:
        str = '関数呼び出し'
    elif lineKind  == LINEKIND.SUBSTITUTE:
        str = '代入処理'
    elif lineKind  == LINEKIND.OTHER:
        str = 'その他'

    return str

#------------------------------------------
# 「(」の後をチェック
# ・True
#　　「(」の後に空白が1つだけあり
# ・False
#　　上記以外
#------------------------------------------
def checkRearSpaceBrackets( line, preStr ):

    #「(」以降の文字列を取得
    #例)「    if (~)」→「(~)」
    str = line.split(preStr)
    afterStr = str[1]

    ret = re.search('^\([ ][^ ]', afterStr)
    if ret == None:
        #「(」の次が空白ではない or 次文字の空白が連続している
        return False

    else:
        #「(」の次が空白1つだけ
        return True


#------------------------------------------
# 制御文のある行（if, for, …）に関して、
# 同じ行に条件を閉じる「)」があるか
#------------------------------------------
def isCloseBracketsOnLine( line ):

    #「(」と「)」の数が同じかどうか
    if line.count('(') == line.count(')'):
        #同じなら、条件が1行に収まっている
        return True
    else:
        return False


#------------------------------------------
# 括弧前後のスペースチェック
# ・if文やwhile文、do-while文、return文等の制御文
# ・関数定義／関数コール
# ・関数プロトタイプ
#------------------------------------------
def checkSpaceBrackets( line, lineKind ):

    #初期値は問題なし
    flg = True

    #制御文
    if (lineKind == LINEKIND.IF_ELSEIF) or (lineKind == LINEKIND.LOOP) or (lineKind == LINEKIND.SWITCH):

        #★複数行の際、「)」の検証が漏れる

        #「(」の直前の空白数
        spaceNum = getFrontSpace('(', line, 0)
        if spaceNum != 1 and spaceNum != 0xFF:
            #制御文は空白1つのみのため、違反
            #print('【文の表現】「(」の左が空白1つではない')
            writeViolation( VIOLATION_TYPE_SENTENCE, '「(」の左が空白1つではない', '')

        #「(」の直後の空白数
        spaceNum = getRearSpace('(', line, 0)
        if spaceNum != 0 and spaceNum != 1 and spaceNum != 0xFF:
            #制御文は空白2つ以上なら、違反
            #print('【文の表現】「(」の右の空白数が多い')
            writeViolation( VIOLATION_TYPE_SENTENCE, '「(」の右の空白数が多い', '')

        #制御文に対応する「)」があるか
        if isCloseBracketsOnLine(line):
            #if文等と同じ行に条件を閉じる「)」あり

            #「)」の直前の空白数
            spaceNum = getFrontSpace(')', line, 0xFF)
            if spaceNum != 0 and spaceNum != 1 and spaceNum != 0xFF:
                #制御文は空白1つのみのため、違反
                #print('【文の表現】「)」の左の空白数が多い')
                writeViolation( VIOLATION_TYPE_SENTENCE, '「)」の左の空白数が多い', '')

    #関数定義／関数コール
    elif lineKind == LINEKIND.CALL_FUNC:
        #「(」の直前の空白数
        spaceNum = getFrontSpace('(', line, 0)
        if spaceNum >= 2 and spaceNum != 0xFF:
            #空白1つのみのため、違反
            #print('【余計な空白】「(」の左に空白が複数あり')
            writeViolation( VIOLATION_TYPE_SENTENCE, '「(」の左に空白が複数あり', '')


        #「(」の直後の空白数
        spaceNum = getRearSpace('(', line, 0)
        if spaceNum >= 2 and spaceNum != 0xFF:
            #空白不要のため、違反
            #print('【余計な空白】「(」の右に空白が複数あり')
            writeViolation( VIOLATION_TYPE_SENTENCE, '「(」の右に空白が複数あり', '')

        #「)」の直前の空白数
        spaceNum = getFrontSpace(')', line, 0)
        if spaceNum >= 2 and spaceNum != 0xFF:
            #空白不要のため、違反
            #print('【余計な空白】「)」の左に空白が複数あり')
            writeViolation( VIOLATION_TYPE_SENTENCE, '「)」の左に空白が複数あり', '')

    #関数プロトタイプ
    elif lineKind == LINEKIND.FUNC_PROTOTYPE:
        #「(」の直前の空白数
        spaceNum = getFrontSpace('(', line, 0)
        if spaceNum != 0 and spaceNum != 0xFF:
            #空白不要のため、違反
            #print('【文の表現】「(」の左が空白1つではない2')
            writeViolation( VIOLATION_TYPE_SENTENCE, '「(」の左が空白1つではない', '')

        #「(」の直後の空白数
        spaceNum = getRearSpace('(', line, 0)
        if spaceNum != 0 and spaceNum != 0xFF:
            #空白不要のため、違反
            #print('【文の表現】「(」の右が空白1つではない')
            writeViolation( VIOLATION_TYPE_SENTENCE, '「(」の右が空白1つではない', '')

        #「)」の直前の空白数
        spaceNum = getFrontSpace(')', line, 0)
        if spaceNum != 0 and spaceNum != 0xFF:
            #空白不要のため、違反
            #print('【文の表現】「)」の左が空白1つではない')
            writeViolation( VIOLATION_TYPE_SENTENCE, '「)」の左が空白1つではない', '')

    else:
        pass


    return

#------------------------------------------
#  指定された文字の後にコメントがあるか
#------------------------------------------
def isFollowComment( word, line ):

    #指定文字が複数存在することを考慮する
    str = line.split(word)
    length = len( str )

    #指定文字で分割した際の、最後の分割文字列
    lastStr = str[ length - 1 ]

    #コメントが存在しているか
    ret = re.search('^ *\/\*', lastStr)
    if ret == None:
        #コメントなし
        return False

    else:
        #コメントあり
        return True


#------------------------------------------
# 前後空白判定の必要な演算子の空白をチェックする
#    【引数】
#    ・判定行
#------------------------------------------
def checkSpaceOperater( line ):

    #ライン文字数-4文字以上の行を参照
    lineLength = len(line)
    if lineLength <= 3:
        return

    #「"」フラグ（Trueとき、""内の文字を参照している）
    doubleFlg = False

    #指定行チェック
    for i, lineWord in enumerate(line):

        #コメントなら判定終了
        if lineWord == "/" and line[i+1] == "*":
            break

        #「"」チェック
        if lineWord == '"':
            if doubleFlg:
                #一度「"」があれば、フラグOFF
                doubleFlg = False
            else:
                #初「"」であれば、フラグON
                doubleFlg = True

        #Trueなら、「""」中の文字のため、スキップ
        if doubleFlg:
            continue

        #-- チェック対象演算子(1文字、前後空白必要) --#
        for opeWord in "<>+-=|/%,":

            #-- ここから空白判定 --#

            #演算子発見
            if opeWord == lineWord:

                #チェック中演算子の前に、別の演算子があるかチェック
                isFront = re.search('[=<>!&|\-\+\/\*%]', line[i - 1])
                if i <= lineLength - 2:
                    isRear = re.search('[=<>!&|\-\+\/\*%]', line[i + 1])
                else:
                    isRear = False

                if not isFront and not isRear:
                    #なしならチェック

                    #-- 前方 --#
                    #「,」はチェック対象外
                    if opeWord != ",":
                        isSpace1 = re.search('[^ ]', line[i - 1])   #1つ前が空白ではない
                        isSpace2 = re.search('[ ]',  line[i - 2])   #2つ前が空白
                        isAllSpace = re.search('[^ ]', line[0:i])    #演算子の前方が全て空白
                        if (isSpace1 or isSpace2) and isAllSpace:
                            #print('【文の表現】「' + opeWord + '」の左が空白1つではない')
                            writeViolation( VIOLATION_TYPE_SENTENCE, '「' + opeWord + '」の左が空白1つではない', '')

                    #文末なら、後ろのチェックは不要
                    if i >= lineLength - 3:
                        break

                    #-- 後方 --#
                    isSpace1 = re.search('[^ ]', line[i + 1])   #1つ後が空白ではない
                    isSpace2 = re.search('[ ]',  line[i + 2])   #2つ後が空白

                    if isSpace1 or isSpace2:
                        #print('【文の表現】「' + opeWord + '」の右が空白1つではない')
                        writeViolation( VIOLATION_TYPE_SENTENCE, '「' + opeWord + '」の右が空白1つではない', '')


        #-- チェック対象演算子類(2文字、前後空白必要) --#
        for opeWord in SPACE_CHECK_OPE_LIST:

            #終端なら、ここで終了
            if i == lineLength - 1:
                break

            #-- ここから空白判定 --#

            #演算子発見
            if (lineWord + line[i + 1]) == opeWord:

                if ('<<=' in line) or ('>>=' in line):
                    #シフト代入なら、判定しない
                    continue

                #-- 前方 --#
                isSpace1 = re.search('[^ ]', line[i - 1])   #1つ前が空白ではない
                isSpace2 = re.search('[ ]',  line[i - 2])   #2つ前が空白
                isAllSpace = re.search('[^ ]', line[0:i])   #演算子の前方が全て空白
                if (isSpace1 or isSpace2) and isAllSpace:
                    #print('【文の表現】「' + opeWord + '」の左が空白1つではない')
                    writeViolation( VIOLATION_TYPE_SENTENCE, '「' + opeWord + '」の左が空白1つではない', '')

                #演算子が終端文字なら、ここで終了
                if i == lineLength - 2:
                    break

                #-- 後方1文字目 --#
                isSpace1 = re.search('[^ ]', line[i + 2])   #1つ後が空白ではない

                if isSpace1:
                    #print('【文の表現】「' + opeWord + '」の右が空白1つではない')
                    writeViolation( VIOLATION_TYPE_SENTENCE, '「' + opeWord + '」の右が空白1つではない', '')

                #-- 後方2文字目 --#
                # 文末がきていれば何もしない
                if len(str(line)) == (i + 3):
                    break

                isSpace2 = re.search('[ ]',  line[i + 3])   #2つ後が空白

                if isSpace2:
                    #print('【文の表現】「' + opeWord + '」の右が空白1つではない')
                    writeViolation( VIOLATION_TYPE_SENTENCE, '「' + opeWord + '」の右が空白1つではない', '')
                
        #-- 「&」「*」は5章よりも前の時だけチェックする --#
        global ProblemNum
        if ProblemNum >= 'hot501':
            continue

        #-- チェック対象演算子類(アドレス関連、前後空白必要) --#
        for opeWord in "&*":

            #-- ここから空白判定 --#

            #演算子発見
            if opeWord == lineWord:

                #チェック中演算子の前に、別の演算子があるかチェック
                isFront = re.search('[=<>!&|\-\+]', line[i - 1])
                if i <= lineLength - 2:
                    isRear = re.search('[=<>!&|\-\+]', line[i + 1])
                else:
                    isRear = False
                if not isFront and not isRear:
                    #なしならチェック

                    #-- 前方 --#
                    #「,」はチェック対象外
                    if opeWord != ",":
                        isSpace1 = re.search('[^ ]', line[i - 1])   #1つ前が空白ではない
                        isSpace2 = re.search('[ ]',  line[i - 2])   #2つ前が空白
                        isAllSpace = re.search('[^ ]', line[0:i])    #演算子の前方が全て空白
                        if (isSpace1 or isSpace2) and isAllSpace:
                            #print('【文の表現】「' + opeWord + '」の左が空白1つではない')
                            writeViolation( VIOLATION_TYPE_SENTENCE, '「' + opeWord + '」の左が空白1つではない', '')

                    #文末なら、後ろのチェックは不要
                    if i >= lineLength - 3:
                        break

                    #-- 後方 --#
                    isSpace1 = re.search('[^ ]', line[i + 1])   #1つ後が空白ではない
                    isSpace2 = re.search('[ ]',  line[i + 2])   #2つ後が空白

                    if isSpace1 or isSpace2:

                        if opeWord == "&":
                            #「＆」の使用がアドレス指定でなければ、ログ出力（アドレス指定の検知は「, &number」となっているかどうか）
                            isAddress = re.search(', *&', line)
                            if not isAddress:
                                #print('【文の表現】「' + opeWord + '」の右が空白1つではない　※アドレス指定なら問題なし')
                                writeViolation( VIOLATION_TYPE_SENTENCE, '「' + opeWord + '」の右が空白1つではない', 'アドレス指定なら問題なし')
                        else:
                            #print('【文の表現】「' + opeWord + '」の右が空白1つではない')
                            writeViolation( VIOLATION_TYPE_SENTENCE, '「' + opeWord + '」の右が空白1つではない', '')

    return

'''
#------------------------------------------
#  指定された文字の前後の空白をチェックする
#    【引数】
#    ・指定文字
#    ・行にあるかを判定する文字列
#    ・判定行
#    ・指定文字の前の判定フラグ
#    ・指定文字の後の判定フラグ
#------------------------------------------
def checkSpaceEachOperater( matchStr, isStr, line, front, rear ):

    #指定文字なしなら、判定対象外
    ret = re.search(isStr, line)
    if ret == None:
        return

    #「指定文字」の後にコメントがあるか
    if isFollowComment( matchStr, line ):
        #問題なし
        return

    #行末に「指定文字」があるか
    last = False

    #行末に「指定文字」があれば、フラグを更新
    ret = re.search(matchStr + '$', line)
    if ret != None:
        last = True

    #行内の「指定文字」数をチェック
    count = line.count( matchStr )
    for i in range( 0, count ):

        #「指定文字」の左をチェック
        spaceNum = getFrontSpace(matchStr, line, i)
        if front and spaceNum != 1:
            #空白がある場合
            #print('【文の表現】「' + matchStr + '」の左が空白1つではない')
            #writeViolation('【文の表現】「' + matchStr + '」の左が空白1つではない')

        #最後の「指定文字」が行末にあれば
        if (i == count - 1) and last:
            #判定終了（右はチェックしない）
            break

        #「指定文字」の右をチェック
        spaceNum = getRearSpace(matchStr, line, i)
        if rear and spaceNum != 1:
            #空白が１つでない場合
            #print('【文の表現】「' + matchStr + '」の右が空白1つではない')
            #writeViolation('【文の表現】「' + matchStr + '」の右が空白1つではない')

    return
'''

#------------------------------------------
#  代入演算子「=」の前後の空白をチェックする
#    【引数】
#    ・判定行
#    ・指定文字の前の判定フラグ
#    ・指定文字の後の判定フラグ
#------------------------------------------
def checkSpaceAssignmentOperater( line, front, rear ):

    #指定文字なしなら、判定対象外
    ret = re.search('=[^=]', line)
    if ret == None:
        return

    #「指定文字」の後にコメントがあるか
    if isFollowComment( '=', line ):
        #問題なし
        return

    #行末に「指定文字」があるか
    last = False

    #行末に「指定文字」があれば、フラグを更新
    ret = re.search(matchStr + '$', line)
    if ret != None:
        last = True

    #行内の「指定文字」をチェック
    count = line.count( matchStr )
    for i in range( 0, count ):

        #最後の「指定文字」が行末にあれば
        if (i == count - 1) and last:
            #判定終了
            break

        #「指定文字」の左をチェック
        spaceNum = getFrontSpace(matchStr, line, i)
        if front and spaceNum != 1:
            #空白がある場合
            #print('【文の表現】「' + matchStr + '」の左が空白1つではない')
            writeViolation( VIOLATION_TYPE_SENTENCE, '「' + matchStr + '」の左が空白1つではない', '')

        #「指定文字」の右をチェック
        spaceNum = getRearSpace(matchStr, line, i)
        if rear and spaceNum != 1:
            #空白が１つでない場合
            #print('【文の表現】「' + matchStr + '」の右が空白1つではない')
            writeViolation( VIOLATION_TYPE_SENTENCE, '「' + matchStr + '」の右が空白1つではない', '')

    return

#------------------------------------------
# 文の表現のチェック
# ・変数定義の変数記述開始位置が揃っているか
# ・1カラム目から79カラム目までの間に記述しているか
#------------------------------------------
def checkSentenceExpression( line, preLine, lineKind ):

    #変数定義の変数記述開始位置が揃っているか
    checkVariableAlign(line, lineKind)

    #1カラム目から79カラム目までの間に記述しているか
    checkMaxColumn(line)

    #スペースチェック「()」
    #制御文、関数など
    checkSpaceBrackets(line, lineKind)

    #空白チェック
    if lineKind != LINEKIND.INCLUDE and lineKind != LINEKIND.DEFINE and lineKind != LINEKIND.PARAMETER:
        checkSpaceOperater( line )

        '''
        checkSpaceEachOperater( ',',  ',',            line, False, True )
        checkSpaceEachOperater( '==', '==',           line, True,  True )
        checkSpaceEachOperater( '!=', '!=',           line, True,  True )
        #checkSpaceEachOperater( '-=', '\-=',           line, True,  True )
        #checkSpaceEachOperater( '+=', '\+=',           line, True,  True )
        ##print('★')
        checkSpaceEachOperater( '<=', '<=',           line, True,  True )
        checkSpaceEachOperater( '>=', '>=',           line, True,  True )
        checkSpaceEachOperater( '&&', '&&',           line, True,  True )
        checkSpaceEachOperater( '||', '||',           line, True,  True )
        checkSpaceEachOperater( '>>', '>>',           line, True,  True )
        checkSpaceEachOperater( '<<', '<<',           line, True,  True )
        #checkSpaceEachOperater( ';',  ';',            line, True,  True )

        ##print('★')
        #文字の前後に特定文字がないかをチェックした上で
        checkSpaceEachOperaterExclusion( '=',  '[^=<>!\+\-]=[^=]', line, True,  True )
        ##print('★★')
        checkSpaceEachOperaterExclusion( '<',  '[^<]<[^<=]',   line, True,  True )
        ##print('★★★')
        checkSpaceEachOperaterExclusion( '>',  '[^\->]>[^>=]', line, True,  True )
        '''

    return

#------------------------------------------
# 5章：「文」の規約違反を検証
#   ・カラムが4つずつか
#   ・余計な空行がないか
#   ・79カラム目までの間にあるか
#------------------------------------------
def verifySentence( line, preLine, lineKind ):

    #カラム開始位置のチェック
    checkNestExpression( line, preLine )

    #文の表現
    checkSentenceExpression( line, preLine, lineKind )

    #使用の制限のチェック
    checkProhibition(line)

    return

#------------------------------------------
#コメント位置が適切か
#------------------------------------------
def checkCommentPos( line ):

    #コメント開始・終了位置（単位：カラム）
    startColumn = 0
    endColumn   = 0

    #「/* ～ */」の文字位置を検索
    ret = re.search('/\*.*\*/', line)
    if ret != None:
        #-- コメント開始位置 --#
        #カラム位置にするために1加算(start()で取れるのはインデックス)
        startColumn = ret.start() + 1

        #-- コメント終了位置 --#
        #end()は、カラム位置調整の加算は不要
        endColumn   = ret.end()

        #2バイト文字数分だけ、位置を進める
        doubleByteNum = count2ByteChar(line)
        endColumn = endColumn + doubleByteNum

    #print(startColumn, '~', endColumn)

    #空行・特定の記述 はここでは判定対称
    if (startColumn == 0) or (startColumn == 1) or (startColumn == 5):
        return;

    #終了位置がずれている場合は、位置ずれ確定
    if endColumn != POS_COMMNET_END:
        #print('【コメント】-位置ずれ-終了位置')
        writeViolation( VIOLATION_TYPE_COMMENT, '位置ずれ-終了位置', '')

    #-- 前方位置ズレ判定 --#
    #49なら問題なし
    if startColumn == POS_COMMNET_START:
        return

    #前方の数が4の倍数にならないなら、位置ずれ
    frontNum = startColumn - 1
    if (frontNum % 4) != 0:
        #print('【コメント】-位置ずれ-前方位置')
        writeViolation( VIOLATION_TYPE_COMMENT, '位置ずれ-前方位置', '')
        return

    #4の倍数でも、コメントが収まるなら不適切
    #※12：「49～78行目に入る全角文字」の数7
    if doubleByteNum <= STANDARD_COMMENT_MAX_NUM:
        ##print('【コメント】-前倒し不要')
        #writeViolation( VIOLATION_TYPE_COMMENT, '前倒し不要')
        pass

    return

#--------------------------
# 指定された文字列が、指定行にいくつあるかカウントする
# (正規表現に対応)
#--------------------------
def getStrNumInLine( isStr, line ):

    pass



#--------------------------
# 型を持つ行が以下のどれであるかを判定
# 　・関数プロトタイプ
# 　・関数定義
# 　・変数宣言
# 　・構造体定義の先頭
# 　・引数
#--------------------------
def judgeMoldType( line ):

    ret = re.search('^int |[^a-zA-Z_]int |^char |[^a-zA-Z_]char |unsigned |float |short |double |struct |void ', line)
    if ret == None:
        return LINEKIND.OTHER

    #-- 型のある行であれば、どんな行か判定 --#

    global ReadLineNum
    global FirstFuncDefinition

    if ('(' in line) and (')' in line) and (';' in line):
        #「(」「)」「;」がある

        #行頭に空白が4つ以上あり
        ret = re.search('^    ', line)
        if ret == None:
            #関数宣言
            #print('関数宣言')
            return LINEKIND.FUNC_PROTOTYPE

    elif ('(' in line) and (';' not in line):
        #「(」があり、「;」がない

        #行頭に空白なし、関数ヘッダ内の記述ではない
        ret1 = re.search('^    ', line)
        ret2 = re.search('^\/\*', line)
        if (ret1 == None) and (ret2 == None) :
            #print('関数定義')
            return LINEKIND.FUNC_DEFINITION

    elif ('(' not in line) and (')' not in line) and (';' in line):
        #「;」のみあれば、変数宣言 or メンバ

        global StructReadFLg
        if StructReadFLg:
            #構造体定義内であれば、メンバ
            #print('メンバ')
            return LINEKIND.STRUCT_MEMBER

        else:
            #そうでないなら、(関数内の)変数
            #print('変数宣言')
            return LINEKIND.VARIABLE

    elif (('struct ' in line) or (' struct ' in line)) and (ReadLineNum < FirstFuncDefinition):
        #struct文字列があり、確認行が「1つ目の関数定義行」よりも前なら
        #構造体定義の先頭
        #print('構造体定義の先頭')
        return LINEKIND.STRUCT

    elif ';' not in line :
        if '=' in line:
            #「=」があれば、変数とみなす
            return LINEKIND.VARIABLE
        else:
            #「=」がなければ、引数とみなす
            return LINEKIND.PARAMETER

    #引数
    return LINEKIND.OTHER


#--------------------------
# ライン種別を取得
#--------------------------
def getLineKind( line ):

    #型あり行の判定
    ret = judgeMoldType(line)
    if ret != LINEKIND.OTHER:
        return ret

    #include
    if '#include' in line :
        return LINEKIND.INCLUDE

    #define
    if '#define' in line :
        return LINEKIND.DEFINE

    #--------------------------------------
    # 制御文が2行以上に渡ってるかを判定する用
    #--------------------------------------
    global CtrlFLg
    if CtrlFLg != LINEKIND.OTHER:
        if '{' in line:
            # 制御文の処理開始ワード「{」があれば、制御条件文（例：for(～～) ）は終了
            CtrlFLg = LINEKIND.OTHER

    if CtrlFLg != LINEKIND.OTHER:
        print("★★=======★★")
        print("", line)
        print("CtrlFLg=", CtrlFLg)
        return CtrlFLg
        print("★★★★")

    #if文、else if文
    ret = re.search(' if | if\(| else[ +]if| else[ +]if\(', line)
    if ret != None:
        # この行で閉じていなければ、制御文扱いとする
        isOneLine = isConditionalStatementOneLine( line )
        if not isOneLine:
            CtrlFLg = LINEKIND.IF_ELSEIF
            
        ##print('if文、else if文')
        return LINEKIND.IF_ELSEIF

    #else文
    ret = re.search(' else | else', line)
    if ret != None:
        #print('else文')
        return LINEKIND.ELSE

    #while文、for文
    ret = re.search(' while | while\(| for | for\(', line)
    if ret != None:
        isOneLine = isConditionalStatementOneLine( line )
        if not isOneLine:
            CtrlFLg = LINEKIND.LOOP

        ##print('ループ文')
        return LINEKIND.LOOP

    #switch文, case文
    ret = re.search(' switch | switch\(| case | default | default:', line)
    if ret != None:
        ##print('switch文, case文')
        return LINEKIND.SWITCH

    #関数コール
    if ( ('(' in line) and (')' in line) and (';' in line) ) \
        or ( ('(' in line) and (';' not in line) ):
        #「(」「)」「;」あり or 「(」あり「;」なし

        #条件式が含まれているか
        ret = hasConditionaloperator(line)

        #条件演算子がないなら
        if not ret:

            #return文ではない
            #if 'return' not in line:
            #「(」の前に関数名がある
            ret = re.search('^ +\(', line)
            if ret == None:
               #print('関数コール')
               return LINEKIND.CALL_FUNC

    #return文
    ret = re.search('return', line)
    if ret != None:
        ##print('return文')
        return LINEKIND.RETURN

    #代入処理
    ret = re.search('[^!=<>]=[^=]', line)
    if ret != None:
        return LINEKIND.SUBSTITUTE

    #その他
    return LINEKIND.OTHER

#--------------------------------------
# 条件演算子が行に含まれているか判定
#--------------------------------------
def hasConditionaloperator(line):

    for ope in CONDITIONAL_OPE:
        if ope in line:
            return True

    return False

#--------------------------------------------------------
# 上の行にコメントを書くことが適切かどうかをチェックする
#   Ture ： 上に書いてOK
#   False： 右に書ける or コメントなし ⇒ NG
#--------------------------------------------------------
def checkTopLineCommentAppropriate( line, preLine ):

    # print("上コメント適切確認開始")
    # print(line)

    # 上の行に処理があれば、違反
    # (その処理のコメントであるため、コメントがそもそもない状態)
    if ';' in preLine:
        return False

    # コメント必須行が「48」カラムまで続いている
    charNum = countLine(line)
    if charNum == 48:
        # コメントが詰まる場合は、問題なし
        return True

    # 次の行に処理が続く(処理が終了していない)場合は、問題なし
    ret  = re.search(';$', line)
    ret2 = re.search('^ *for|^ *while|^ *if', line)
    # if (ret == None) or (ret != None and ret2 != None):
    if (ret != None) and (ret2 != None):
        return True

    # 上の行のコメント開始位置を取得(単位：カラム)
    commentStartPos = preLine.find('/*') + 1

    # 「上の行のコメント開始位置」と「処理行の処理終了位置」の差が「1」以下
    if ( commentStartPos - charNum ) <= 1:
        # 上にしかコメントをかけないため、問題なし
        return True
    else:
        # 右にコメントかけるため、違反
        return False


#------------------------------------
# コメント必須箇所にコメントがあるか
#------------------------------------
def isCommentExist( line, preLine, lineKind ):

    # コメント必須文ではないなら、検証不要
    if lineKind == LINEKIND.OTHER or lineKind == LINEKIND.FUNC_DEFINITION or lineKind == LINEKIND.INCLUDE:
        return

    # 判定対象行が制御文の場合、「2行目以降の条件文」であれば、コメント不要
    isSecondLine = isSecondLineConditionalStatement( line, lineKind )
    print("=============")
    print("", line)
    print("isSecondLine=", isSecondLine)
    if isSecondLine:
        return

    #=============================
    # コメント必須文の判定
    #=============================

    # 右にコメントがあるか
    if '/*' in line:
        # 右にあるなら、問題なし
        return

    #=================
    # 右にコメントなし
    #=================

    # 必須行の種類を表示用文字列として保持
    msgKind = getLineKindStr(lineKind)

    # 上の行を確認。ただし、宣言時の記述を省くように検索
    ret = re.search('\/\*[A-Za-z ]*\*\/', preLine)
    if (('/*' not in preLine) or ( ret != None )) :
        
        # 制御文中の代入処理なら違反ではない
        if (lineKind == LINEKIND.SUBSTITUTE) and (CtrlFLg != LINEKIND.OTHER):
            return

        # 上にもコメントがないなら、違反
        writeViolation( VIOLATION_TYPE_REQUIRED_COMMENT, 'なし_' + msgKind, '')
        return

    #=================
    # 上にコメントあり
    #=================

    # 上に書いてよい状態かチェック
    ret = checkTopLineCommentAppropriate( line, preLine )
    if not ret:

        # 制御文中の代入処理なら違反ではない
        if (lineKind == LINEKIND.SUBSTITUTE) and (CtrlFLg != LINEKIND.OTHER):
            return

        # 上の行でのコメントは不適切
        # print('【必須コメント】上行へのコメント記載は不適切_' + msgKind)
        writeViolation( VIOLATION_TYPE_REQUIRED_COMMENT, '上行へのコメント記載は不適切_' + msgKind, '')

    return


#------------------------------
# 指定された制御文が1行のみかどうか
#   
#   例1) if( ~~~~~~ ) : true
#
#   例2) if( ~~~~~~   : false
#            ~~~ )
#------------------------------
def isConditionalStatementOneLine( line ):

    #=======================
    # 「(」と「)」の数で判定
    #=======================
    openNum = line.count('(')
    closeNum = line.count(')')

    # 括弧の数が不一致なら、2行目以降に続いている
    if openNum != closeNum:
        # 1行ではない
        return False

    # 1行のみ
    return True

#------------------------------
# 2行目以降の条件文かどうかの判定
#   
#   例)  for ( ~~~　　：false
#            ~~~~　　 ：true
#            ~~~~ )　 ：true
#------------------------------
def isSecondLineConditionalStatement( line, lineKind ):

    #==============
    # 制御文かどうか
    #==============
    # そもそも、制御文でないなら何もしない
    if ( lineKind != LINEKIND.IF_ELSEIF and
         lineKind != LINEKIND.LOOP ):
         return False
        
    #==============
    # 制御文
    #==============
    # if, else if 判定
    ret = re.search(' if | if\(| else[ +]if| else[ +]if\(', line)
    if ret != None:
        # 1行目に存在するワードがあるなら、2行目以降の制御文ではない
        return False

    # for, while 判定
    ret = re.search(' while | while\(| for | for\(', line)
    if ret != None:
        # 1行目に存在するワードがあるなら、2行目以降の制御文ではない
        return False


    # 2行目以降と判定
    return True

#--------------------------
# 全般の内容
#　・コメント中の入れ子（コメント中のコメント）をしていないか
#　・複数行にまたがるコメントをしていないか
#--------------------------
def checkCommentWhole( line ):

    #-- コメント中の入れ子チェック --#
    #※「//」の有無で判定
    if '//' in line:
        #print('【コメント】入れ子コメントの可能性あり(「//」を使用している)')
        writeViolation( VIOLATION_TYPE_COMMENT, '入れ子コメントの可能性あり(「//」を使用している)', '')

    #-- 複数行にまたがるコメントチェック --#
    if ( '/*' in line ) and ( '*/' not in line ):
        #「/*」があって「*/」のない行は、複数行コメント
        #print('【コメント】複数行コメントは禁止')
        writeViolation( VIOLATION_TYPE_COMMENT, '複数行コメントは禁止', '')

    return

#--------------------------
# 検証：コメント
#--------------------------
def verifyComment( line, preLine, lineKind ):

    #コメントの開始位置と終了位置をチェック
    checkCommentPos(line)

    #必須コメントの有無をチェック
    isCommentExist(line, preLine, lineKind)

    #全般の内容
    checkCommentWhole(line)

#--------------------------
# define記載時の宣言文があるか
#--------------------------
def isDefineDeclaration( line, preLine ):

    #前回位置が0以上なら、検証済み
    global PreDefine1stPos
    if PreDefine1stPos > 0:
        return

    #初めのdefineの上行に、宣言があるか
    if preLine != DECLARATION_DEFINE:
        #print('【define】宣言コメント(USER DEFINE)エラー  ※1行空行ある場合ならセーフ')
        writeViolation( VIOLATION_TYPE_DEFINE, '宣言コメント(USER DEFINE)エラー', '空行がある場合も検知対象としています。空行の場合、宣言文は目視で確認をお願いします')

    return

#--------------------------
# defineの文字列１，２の位置が適切かをチェック
#--------------------------
def checkDefineAlign( line ):

    #半角スペースで分割
    str = re.split( ' +', line )

    #文字列１、２のカラム位置を保持
    firstPos  = line.find( str[1] ) + 1
    secondPos = line.find( ' ' + str[2] + ' ' ) + 1   #空白文字を含めているのは、define名側に値の文字列が含まれている場合があるため

    #前回位置の取得
    global PreDefine1stPos
    global PreDefine2ndPos

    #2つ目の宣言以降をチェックしていく
    if PreDefine1stPos > 0:
        #位置ずれチェック
        if firstPos != PreDefine1stPos:
            #print('【define】define名の記述位置が上の行と揃っていない(以降すべてずれている可能性あり)')
            writeViolation( VIOLATION_TYPE_DEFINE, 'define名の記述位置が上の行と揃っていない(以降すべてずれている可能性あり)', '')

        if secondPos != PreDefine2ndPos:
            #print('【define】定義値の記述位置が上の行と揃っていない(以降すべてずれている可能性あり)')
            writeViolation( VIOLATION_TYPE_DEFINE, '定義値の記述位置が上の行と揃っていない(以降すべてずれている可能性あり)', '')

    #前回位置として保持
    PreDefine1stPos = firstPos
    PreDefine2ndPos = secondPos

    return

#--------------------------
# Extern変数チェック
#--------------------------
def checkExternVal( line, preLine ):

    #extern行ではないなら、検証対象外
    pos = line.find('extern ')
    if pos == -1:
        return

    #記述位置が先頭か
    if pos != 0:
        #print('【define】記述位置が行の先頭ではない')
        writeViolation( VIOLATION_TYPE_EXTERNAL, '記述位置が行の先頭ではない', '')

    #宣言文があるか
    isExternVarDeclaration(line, preLine)

    #変数名の記述位置が適切か
    checkExternalValPos(line)

    return

#--------------------------
# extern変数の宣言文があるか
#--------------------------
def isExternVarDeclaration( line, preLine ):

    #前回位置が0以上なら、検証済み
    global PreExternVarPos
    if PreExternVarPos > 0:
        return

    #初めのexternの上行に、宣言があるか
    if preLine != DECLARATION_EXTERNAL:
        #print('【define】宣言コメント(EXTERNAL DEFINITION)エラー  ※1行空行ある場合ならセーフ')
        writeViolation( VIOLATION_TYPE_EXTERNAL, '宣言コメント(EXTERNAL DEFINITION)エラー', '空行がある場合も検知対象としています。空行の場合、宣言文は目視で確認をお願いします')

    return

#--------------------------
# extern変数の記述位置が揃っているか
#--------------------------
def checkExternalValPos( line ):

    global PreExternVarPos

    #半角スペースで分割
    str = re.split( ' +', line )

    #変数名のカラム位置
    pos  = line.find( str[2] ) + 1

    #前回位置と不一致なら
    if PreExternVarPos > 0:
        if pos != PreExternVarPos:
            writeViolation( VIOLATION_TYPE_EXTERNAL, '変数名の記述位置が上の行と揃っていない(以降すべてずれている可能性あり)', '')

    #前回位置として保持
    PreExternVarPos = pos
    return

#--------------------------
# 変数名のカラム位置を取得
# 　空白以外の文字位置(2回目)で判断する
#--------------------------
def getNameColumnPos( line ):

    #文字判定状態
    # 0： 先頭の空白
    # 1： 型の文字列
    # 2： 型の文字列の後の空白
    # ---------------------------
    # 2の状態で、空白以外の文字が見つかれば、それが変数名の先頭文字
    state = 0

    #「struct」がある場合
    if ' struct ' in line:
        #「struct」文字列を空白文字にして、カウントから除外させる
        line = line.replace(' struct ', '        ')

    elif 'struct ' in line:
        #「struct」文字列を空白文字にして、カウントから除外させる
        line = line.replace('struct ', '       ')

    #「unsigned」がある場合
    elif ' unsigned ' in line:
        #「unsigned」文字列を空白文字にして、カウントから除外させる
        line = line.replace(' unsigned ', '          ')

    elif 'unsigned ' in line:
        #「unsigned」文字列を空白文字にして、カウントから除外させる
        line = line.replace('unsigned ', '         ')

    #「signed」がある場合
    elif ' signed ' in line:
        #「signed」文字列を空白文字にして、カウントから除外させる
        line = line.replace(' signed ', '        ')

    elif 'signed ' in line:
        #「signed」文字列を空白文字にして、カウントから除外させる
        line = line.replace('signed ', '       ')


    #「static」がある場合
    if ' static ' in line:
        #「signed」文字列を空白文字にして、カウントから除外させる
        line = line.replace(' static ', '        ')

    elif 'static ' in line:
        #「signed」文字列を空白文字にして、カウントから除外させる
        line = line.replace('static ', '       ')


    #1文字ずつチェック
    for i, word in enumerate(line):
        #半角スペース
        if word == ' ':
            #一度、文字が見つかっていれば
            if state == 1:
                #型の後の空白を見つけ中
                state = 2

        #半角スペース以外
        else:
            if state == 0:
                state = 1

            elif state == 2:
                #変数名の先頭文字を発見
                break

    #i はインデックスなので、加算してカラム位置とする
    return i + 1

#--------------------------
# 変数の記述開始位置が揃っているかチェック
#--------------------------
def checkVariableAlign( line, lineKind ):

    #変数宣言文以外
    if lineKind != LINEKIND.VARIABLE:
        #判定対象外
        return

    #変数名のカラム位置を取得
    pos = getNameColumnPos(line)

    #前回位置の取得
    global PreVar1stPos

    #2つ目の宣言以降をチェックしていく
    if PreVar1stPos > 0:
        #変数名の記述位置をチェック
        #print('位置→', pos)
        if pos != PreVar1stPos:
            #print('【変数宣言】上の行との記述位置ずれ(以降すべてずれている可能性あり)')
            writeViolation( VIOLATION_TYPE_VARIABLE, '上の行との記述位置ずれ(以降すべてずれている可能性あり)', '')

    #前回位置として保持
    PreVar1stPos = pos

    return

#--------------------------
# define名の最大文字数チェック
#--------------------------
def checkDefineName( line ):

    #半角スペースで分割
    #str = line.split(' ')
    str = re.split( ' +', line )

    #define名
    defineName = str[1]

    #最大文字数の超過を判定
    if len(defineName) > MAX_DEFINE_NUM:
        #print( '【define】define名文字数超過' )
        writeViolation( VIOLATION_TYPE_DEFINE, 'define名文字数超過', '')

    return

#--------------------------
# defineチェック
#--------------------------
def checkDefine( line, preLine ):

    #define行ではないなら、検証対象外
    pos = line.find('#define')
    if pos == -1:
        return

    #記述位置が先頭か
    if pos != 0:
        #print('【define】記述位置が行の先頭ではない')
        writeViolation( VIOLATION_TYPE_DEFINE, '記述位置が行の先頭ではない', '')

    #宣言文があるか
    isDefineDeclaration(line, preLine)

    #文字列と値の記述位置が適切か
    checkDefineAlign(line)

    #定義が20文字いないか
    checkDefineName(line)

    #※※※ コメントは別箇所で検証している ※※※

    return


#--------------------------
# 構造体チェック
#   ・宣言コメントのフォーマット
#   ・余計な空行の有無
#   ・メンバ記述位置
#   ・P.12の規約に沿ったフォーマットか
#   　　・「{」の位置
#   　　・「}」の位置
#   　　・structが行頭か
#   　　・メンバが4カラム目からの記載か
#   ※必須コメントがあるかは、別箇所にてチェック
#--------------------------
def checkStruct( line, preLine, lineKind ):

    global StructReadFLg
    global StructDeclarationFLg
    global PreMember1stPos

    #構造体先頭あり
    if lineKind == LINEKIND.STRUCT:
        StructReadFLg   = True      #構造体の記述開始
        PreMember1stPos = 0         #メンバ記述位置初期化

        #-- 宣言コメントのチェック --#
        #まだチェックしていないなら
        if not StructDeclarationFLg:
            if preLine != DECLARATION_STRUCTURE:
                #print('【構造体】宣言コメントエラー  ※1行空行ある場合ならセーフ')
                writeViolation( VIOLATION_TYPE_STRUCT, '宣言コメント(STRUCTURE DEFINITION)エラー', '空行がある場合も検知対象としています。空行の場合、宣言文は目視で確認をお願いします')

            #チェックしたため、フラグ更新
            StructDeclarationFLg = True

        #-- 「{」が構造体宣言の右にあるか --#
        if '{' in line:
            #print('【構造体】「{」がstructの右にある')
            writeViolation( VIOLATION_TYPE_STRUCT, '「{」がstructの右にある', '')

        #-- 行が「struct」で始まっているか --#
        ret = re.search( '^struct', line )
        if ret == None:
            #print('【構造体】「struct」を行頭から記載していない')
            writeViolation( VIOLATION_TYPE_STRUCT, '「struct」を行頭から記載していない', '')

    #構造体の記述でないなら、判定なし
    if not StructReadFLg:
        return

    #-- 空行チェック --#
    if countLine(line) == 0:
        #print('【構造体】余計な空行あり')
        writeViolation( VIOLATION_TYPE_STRUCT, '余計な空行あり', '')

    #-- メンバの記述位置が合っているか --#
    #メンバ行
    if lineKind == LINEKIND.STRUCT_MEMBER:

        #変数名のカラム位置を取得
        pos = getNameColumnPos(line)
        #2つ目のメンバ以降
        if PreMember1stPos > 0:
            #記述位置が上のメンバと不一致
            if pos != PreMember1stPos:
                #print('【構造体】メンバ記述位置が上の行と揃っていない(以降すべてずれている可能性あり)')
                writeViolation( VIOLATION_TYPE_STRUCT, 'メンバ記述位置が上の行と揃っていない(以降すべてずれている可能性あり)', '')

        #上の行の記述位置として保持
        PreMember1stPos = pos

    #「}」の行
    if '}' in line:
        #-- 「}」が行頭にきているか --#
        ret = re.search( '^\}', line )
        if ret == None:
            #print('【構造体】「}」が行頭にない')
            writeViolation( VIOLATION_TYPE_STRUCT, '「}」が行頭にない', '')

        #構造体終了
        StructReadFLg = False

    return


#--------------------------
# 記述位置判定
#--------------------------
def checkWritePosAline( line, pos2 ):
    #やっぱり関数化なし
    psss

#--------------------------
# 関数プロトタイプの記載フォーマットをチェックする
#--------------------------
def checkFuncPrototypeFormat( line ):

    global PreMember1stPos

    #★2行になっていたとき、現状では関数プロトタイプと認識していないため、改修必要

    #一行に記載されているか(「;」がないなら複数行になっている)
    if ';' not in line:
        #print('【文の表現】複数行に記載されている')
        writeViolation( VIOLATION_TYPE_SENTENCE, '複数行に記載されている', '')
        return

    #-- 先頭から記載されているか --#
    ret = re.search('^ ', line)
    if ret != None:
        #print('【文の表現】行の先頭から記載されていない')
        writeViolation( VIOLATION_TYPE_SENTENCE, '行の先頭から記載されていない', '')
        return

    #-- 関数名の記述位置が揃っているか --#

    #変数名のカラム位置を取得
    pos = getNameColumnPos(line)
    #2つ目のメンバ以降
    if PreMember1stPos > 0:
        #記述位置が上のメンバと不一致
        if pos != PreMember1stPos:
            #print('【文の表現】関数名の記述位置が上と揃っていない(以降すべてずれている可能性あり)')
            writeViolation( VIOLATION_TYPE_SENTENCE, '関数名の記述位置が上と揃っていない(以降すべてずれている可能性あり)', '')

    #上の行の記述位置として保持
    PreMember1stPos = pos

    #-- 括弧前後のスペース、「,」後のスペースなど --#
    #※別箇所にてチェック

    return

#--------------------------
# 関数プロトタイプチェック
#   ・宣言コメントのフォーマット
#   ・引数ない場合、voidと明記しているか
#   ・関数名の記述位置
#   ※「()」や「,」の前後のスペースは、別箇所にてチェック
#   ※必須コメントがあるかは、別箇所にてチェック
#--------------------------
def checkFuncPrototype( line, preLine, nextLine, lineKind ):

    global FuncPrototypeReadFLg
    global PreMember1stPos

    #未読み込み
    if not FuncPrototypeReadFLg:

        #関数プロトタイプではない
        if lineKind != LINEKIND.FUNC_PROTOTYPE:
            return

        else:
            #関数プロトタイプ
            FuncPrototypeReadFLg = True       #記述開始
            PreMember1stPos      = 0          #メンバ記述位置初期化

            #フォーマットチェック
            checkFuncPrototypeFormat(line)

            #-- 宣言コメントのチェック --#
            if preLine != DECLARATION_FUNCTION:
                #print('【文の表現】宣言コメントエラー  ※1行空行ある場合ならセーフ')
                writeViolation( VIOLATION_TYPE_SENTENCE, '宣言コメント(FUNCTION PROTOTYPE)エラー', '空行がある場合も検知対象としています。空行の場合、宣言文は目視で確認をお願いします')

    #判定中
    else:

        #関数プロトタイプ
        if lineKind == LINEKIND.FUNC_PROTOTYPE:
            #フォーマットチェック
            checkFuncPrototypeFormat(line)

            return

        #関数ヘッダ先頭 判定用
        ret = re.search('^\/\*', line)
        #上の行におかれたコメント行 判定用
        ret2 = re.search('^ *\/\*', line)

        #関数ヘッダの先頭 or ( OTHERの行 and 空行以外 and )
        if (ret != None) or ((lineKind == LINEKIND.OTHER) and (countLine(line) != 0) and (ret2 == None)):
            #関数プロトタイプの範囲終わり
            FuncPrototypeReadFLg = False
            PreMember1stPos      = 0

            return

        #空行
        if countLine(line) == 0:
            #-- 次の行で違反か判別 --#

            ret = re.search('^ +\/\*', nextLine)
            nextLineKind = getLineKind(nextLine)

            #空行
            if countLine(nextLine) == 0:
                #print('【文の表現】余計な空行')
                writeViolation( VIOLATION_TYPE_SENTENCE, '余計な空行', '')

            #関数プロトタイプ
            elif nextLineKind == LINEKIND.FUNC_PROTOTYPE:
                #print('【文の表現】余計な空行')
                writeViolation( VIOLATION_TYPE_SENTENCE, '余計な空行', '')

            #上の行におかれたコメント行
            elif ret != None:
                #print('【文の表現】余計な空行')
                writeViolation( VIOLATION_TYPE_SENTENCE, '余計な空行', '')

            return

        return

#--------------------------
# プリプロセッサチェック
# ・制御文字の先頭に記載する'#'は1カラム目から記述しているか
# ・''#'と次の制御文字との間に空白（スペース）を入れていないか
#--------------------------
def checkPreprocessor( line ):

    if '#' not in line:
        #「#」ないなら、プリプロセッサ行ではない
        return

    #-- 「#」が1カラム目からか --#
    ret = re.search('^#', line)
    if ret == None:
        #print('【プリプロセッサコマンド】＃が１カラム目にない')
        writeViolation( VIOLATION_TYPE_PREPROCESSOR, '＃が１カラム目にない', '')

    #-- 空白ないか --#
    ret = re.search('# ', line)
    if ret != None:
        #print('【プリプロセッサコマンド】＃の次に空白がある')
        writeViolation( VIOLATION_TYPE_PREPROCESSOR, '＃の次に空白がある', '')

#--------------------------
# 検証：関数外情報
#--------------------------
def verifyOutsideFunc( line, preLine, nextLine, lineKind ):

    #defineチェック
    checkDefine( line, preLine )

    #extern変数チェック
    checkExternVal( line, preLine )

    #構造体チェック
    checkStruct( line, preLine, lineKind )

    #関数プロトタイプチェック
    checkFuncPrototype( line, preLine, nextLine, lineKind )

    #プリプロセッサコマンドチェック
    checkPreprocessor( line )

#--------------------------
# 検証：出力メッセージ
#--------------------------
def verifyOutputMessage( line, lineKind ):

    global CallPrintfFLg
    global DisplayMsgManager

    # printf()コール中ではない場合、本ラインのコールチェックから
    if not CallPrintfFLg:
        CallPrintfFLg = isCallPrintf(line)

    # print( 'CallPrintfFLg=' + CallPrintfFLg )
    # print( line )
    # print( CallPrintfFLg )

    # printf()コール中なら検証
    if CallPrintfFLg:
        # 出力メッセージの検証
        DisplayMsgManager.collationMessage(line)
        # printf()終了ラインの場合、フラグを落とす
        CallPrintfFLg = not isEndPrintf(line)

    # print( 'CallPrintfFLg=' + CallPrintfFLg )
    # print( '=検証後のフラグ=' )
    # print( line )
    # print( CallPrintfFLg )
    # print( '=============' )


#-----------------------------------------
# 指定ラインが「printf()」をコールしているか
#-----------------------------------------
def isCallPrintf( line ):

    # printfが含まれているかチェック
    ret = re.search('printf', line)
    if ret == None:
        return False
    else:
        return True

#-----------------------------------------
# 指定ラインで「printf()」処理が終了しているか
#-----------------------------------------
def isEndPrintf( line ):

    # printfコール終了の記述が含まれているかチェック
    ret = re.search('\).*;', line)
    if ret == None:
        return False
    else:
        return True


#----------------------------------
# 変数の定義は1行1個となっているか
#----------------------------------
def checkVarOnePerLine(line, lineKind):

    #変数宣言文以外
    if lineKind != LINEKIND.VARIABLE:
        #判定対象外
        return

    #「,」があり、「=」がなければ違反
    if ',' in line and '=' not in line:
        #print('【識別子の定義】変数の定義は1行1個')
        writeViolation( VIOLATION_TYPE_IDENTIFIER, '変数の定義は1行1個', '')

    return

#----------------------------------------------------------
#　すべて小文字 or 先頭文字を英大文字として記述しているか
#　  変数名、構造体タグ名に関して、
#　　大文字が連続していないかで判定する
#----------------------------------------------------------
def checkLowercase(line, lineKind):

    #変数名 or 構造体タグ or 構造体メンバを抽出
    if lineKind == LINEKIND.VARIABLE or lineKind == LINEKIND.STRUCT_MEMBER:
        #変数名 or 構造体メンバ

        #「struct」がある場合
        if 'struct' in line:
            #「struct」文字列を空白文字にする
            line = line.replace(' struct ', ' ')

        #配列がある場合([])
        if '[' in line:
            #「[」よりも前の文字列を取得
            tmp  = line.split('[')
            line = tmp[0]

        #名称抽出
        tmp = re.split(' +', line)

        # 配列の最後尾のindexが変数名を指すindex
        varIndex = len( tmp ) - 1

        #先頭が空白で始まる場合、変数名は3つ目に格納される
        #    char    Tel
        # ↓
        #['', 'char', 'Tel']
        name = tmp[varIndex]

    elif lineKind == LINEKIND.STRUCT:
        #構造体タグ名

        #先頭に空白を入れてしまっている場合を考慮し、「struct」は空白にする
        line = line.replace(' struct ', ' ')

        #名称抽出
        tmp = re.split(' +', line)

        #タグ名は2つ目に格納される
        # struct Name_List
        # ↓
        #  Name_List
        # ↓
        # ['', 'Name_List']
        name = tmp[1]

    else:
        #対象外
        return

    #大文字一つ発見フラグ
    #※大文字を見つけた時、Trueに更新する
    firstOne = False

    #大文字が連続していないかチェック
    for i in name:
        #大文字なら
        if i.isupper():
            if firstOne:
                #大文字が1つ見つかっている状態なら、違反
                #print('【識別子の定義】すべて小文字 or 先頭文字を英大文字として記述していない')
                writeViolation( VIOLATION_TYPE_IDENTIFIER, 'すべて小文字 or 先頭文字を英大文字として記述していない', '')
                break
            else:
                #1つ目発見のフラグを立てる
                firstOne = True

        else:
            #小文字ならフラグリセット
            firstOne = False

    return

#--------------------------
#　検証：「2章. 関数の記述」
#　・引数の定義
#　・関数名と括弧'('との間に空白（スペース）を入れていないか
#--------------------------
def verifyFunction(line, preLine, nextLine, lineKind):

    #引数の定義チェック
    checkParameters(line, preLine, nextLine, lineKind)

    #関数名と括弧'('との間に空白チェック：定義
    checkFuncnameSpace(line, lineKind)

    #関数名と括弧'('との間に空白チェック：コール
    checkCallFuncnameSpace(line)

    return

#--------------------------
#　引数チェック
#　・引数がない場合、voidを指定して定義しているか
#　・引数がある場合、コーディング規約P.10の書式となっているか
#--------------------------
def checkParameters(line, preLine, nextLine, lineKind):

    #引数なし
    checkParametersNone(line, nextLine, lineKind)

    #引数あり
    checkParametersExisting(line, preLine, lineKind)

    return

#--------------------------
# 引数がない場合、voidを指定して定義しているか
#--------------------------
def checkParametersNone(line, nextLine, lineKind):

    #関数定義行でないなら終了
    if lineKind != LINEKIND.FUNC_DEFINITION:
        return

    #次の行に引数ありの場合も終了
    nextLineKind = getLineKind(nextLine)
    if nextLineKind == LINEKIND.PARAMETER:
        return

    #次の行にvoidを記載していれば、違反
    if 'void' in nextLine:
        #違反
        #print('【関数の記述】voidは関数名と同行に記載する')
        writeViolation( VIOLATION_TYPE_FUNCTION, 'voidは関数名と同行に記載する', '')

        return

    #引数の()内に何も記述がないなら違反
    ret = re.search('\( *\)$|\( *$', line)
    if ret != None:
        #違反
        #print('【関数の記述】引数がない場合、voidを指定して定義する')
        writeViolation( VIOLATION_TYPE_FUNCTION, '引数がない場合、voidを指定して定義する', '')

    return

#--------------------------
# 引数がある場合、コーディング規約P.10の書式となっているか
#--------------------------
def checkParametersExisting(line, preLine, lineKind):

    #引数行でないなら終了
    if lineKind != LINEKIND.PARAMETER:
        return

    #-- 先頭から記載されているか --#
    ret = re.search('^ ', line)
    if ret != None:
        #先頭が空白なら、違反
        #print('【関数の記述】引数は行頭から記載する')
        writeViolation( VIOLATION_TYPE_FUNCTION, '引数は行頭から記載する', '')

    #-- 引数名の記載位置は揃っているか --#
    global PreParameterPos

    #引数名のカラム位置を取得
    pos = getNameColumnPos(line)

    checkPos = 0

    #1つ目の引数
    if PreParameterPos == 0:
        #関数定義の記述位置
        #print('★1つ目の引数:ルートチェック')
        checkPos = getNameColumnPos(preLine)

    #2つ目の引数以降
    elif PreParameterPos > 0:
        #前回引数の記述位置
        checkPos = PreParameterPos

        #記述位置が上の引数と不一致
        if pos != checkPos:
            #print('★不一致:ルートチェック')
            #print('【関数の記述】引数名の記述位置が上と揃っていない(以降すべてずれている可能性あり)')
            writeViolation( VIOLATION_TYPE_FUNCTION, '引数名の記述位置が上と揃っていない(以降すべてずれている可能性あり)', '')

    #上の行の記述位置として保持
    PreParameterPos = pos

    return

#--------------------------
# 関数名と括弧'('との間に空白チェック：定義
#--------------------------
def checkFuncnameSpace(line, lineKind):

    #関数定義行でないなら終了
    if lineKind != LINEKIND.FUNC_DEFINITION:
        return

    #「(」の右に空白がなければOK
    ret = getFrontSpace('(', line, 0)
    if ret != 0:
        #違反
        #print('【関数の記述】関数名と括弧(との間は空白なし')
        writeViolation( VIOLATION_TYPE_FUNCTION, '関数名と括弧(との間は空白なし', '')

    return

#--------------------------
# 関数名と括弧'('との間に空白チェック：コール
#--------------------------
def checkCallFuncnameSpace(line):

    # ヘッダ内の記述なら何もしない
    ret = re.search('^\/\*', line)
    if ret != None:
        return

    # 研修問題で使用している関数の存在を確認
    ret = re.search('printf|scanf|getchar|putchar|strlen|\
        Calculate|Numeric_Count|List_Display|menu_display|select_input|compute^_|\
        Num_Swap|Str_Length|strlen|Str_Concat|Max_Search|\
        Input_Confirm|Data_Input|Data_Display|Menu_Display|Data_Sort\
        ', line)
    
    # なければ何もしない
    if ret == None:
        return

    # コメント中の文言なら何もしない
    if ('/*' in line):
        return

    # マッチ結果から、「検証文字列の次にある文字」を取得
    # 例）「putchar(input_char) ;」の場合
    #     「(」を取得
    matchWord1NextPos = ret.end()
    matchWord1NextChar = line[matchWord1NextPos]

    # 関数名の次にある文字が想定する文字でなければ
    if matchWord1NextChar != '(':
        # 違反
        # print('【関数の記述】関数名と括弧(との間は空白なし')
        writeViolation( VIOLATION_TYPE_FUNCTION, '関数名と括弧(との間は空白なし', '')

    return

#--------------------------
#　検証：「3章. 識別子の定義」
#　・変数の定義は1行1個となっているか
#　・変数名、構造体タグ名は以下の通りか
#　　→すべて小文字 or 先頭文字を英大文字として記述しているか
#--------------------------
def verifyIdentifier(line, preLine, lineKind):

    #変数の定義は1行1個となっているか
    checkVarOnePerLine(line, lineKind)

    #すべて小文字 or 先頭文字を英大文字として記述しているか
    checkLowercase(line, lineKind)


#--------------------------
#　提出されたファイル名のフォーマットをチェック
#　(とりあえず、以下だけみとく)
#　・hotxxx があるか(6文字かだけみる)
#--------------------------
def verifyFileName(fileName):

    #ファイル名内の「hotxxx」を取得
    if '_'  in fileName:
        #「_」あり
        tmp = fileName.split('_')
        hot = tmp[0]

    else:
        #「_」なし
        tmp = fileName.split('.')
        hot = tmp[0]

    #必ず6文字になるはず
    length = len( hot )
    if length != 6:
        ##print('【提出ファイル名】hotxxx となっていない')
        #writeViolation('【提出ファイル名】', 'hotxxx となっていない（本ファイルの検証をスルーする）')

        #return False

        pass

    return True

#--------------------------
# 関数ヘッダチェック
#--------------------------
def checkFuncHeader( startPos, endPos, code ):

    #判定中のライン行目
    # 本関数内で、適切な位置を設定する
    global ReadLineNum
    ReadLineNum = 0

    #ヘッダ位置がファイルヘッダの位置にある場合、ヘッダそのものの記載漏れ
    if startPos <= 1:
        #print('【関数ヘッダ】ヘッダそのものがない')    #指摘行の明記はしない
        writeViolation( VIOLATION_TYPE_FUNCHEADER, 'ヘッダそのものがない', '')
        return

    #ヘッダは最低でも5行存在するはずのため、5行ないならまず不足している違反だけ出力する
    #(理由：以降のチェックでは、少なくとも必須の5行があることを前提としてチェックしているため)
    if (endPos - startPos) < 4:
        #print('【関数ヘッダ】フォーマット誤り-必須行のいずれかがない')    #指摘行の明記はしない
        writeViolation( VIOLATION_TYPE_FUNCHEADER, 'フォーマット誤り-必須行のいずれかがない', '')
        return

    ReadLineNum = startPos + 1

    #先頭行
    line = code[startPos]
    if line != FIXED_STR_FUNCHEADER_TITLE:
        print('【関数ヘッダ】フォーマット誤り')
        print(line)
        print(line)
        
        writeViolation( VIOLATION_TYPE_FUNCHEADER, 'フォーマット誤り', '')
        ##print('対象行=', line)

    ReadLineNum = startPos + 2

    #関数名の行
    line = code[startPos + 1]
    ret = re.search(FIXED_STR_FUNCHEADER_FILENAME, line)
    if ret == None:
        print('【関数ヘッダ】フォーマット誤り2')
        print(line)
        writeViolation( VIOLATION_TYPE_FUNCHEADER, 'フォーマット誤り', '')
        ##print('対象行=', line)

    ReadLineNum = startPos + 3

    #内容の行
    line = code[startPos + 2]
    ret = re.search(FIXED_STR_FUNCHEADER_CONTENTS, line)
    if ret == None or not check62Column( line ):
        #print('【関数ヘッダ】フォーマット誤り')
        writeViolation( VIOLATION_TYPE_FUNCHEADER, 'フォーマット誤り', '')
        ##print('対象行=', line)

    #-- 内容とリターンは複数行の可能性も考慮する --#

    returnLineIndex = 0

    #リターン行の位置を特定
    for i in range(startPos + 3, endPos):
        line = code[i]

        #リターン文の前方のフォーマットエラーがある場合を考慮し、検索文字列は最小限にしておく
        if '/*  リ' in line:
            returnLineIndex = i
            break
    else:
        ReadLineNum = i + 1

        #リターン文が見つからないなら、違反
        #print('【関数ヘッダ】リターン文がない or リターン文フォーマットエラー')        #指摘行の明記はしない
        writeViolation( VIOLATION_TYPE_FUNCHEADER, 'リターン文がない or リターン文フォーマットエラー', '')

        #判定はここで一旦終了
        return

    #内容行の続き
    for i in range(startPos + 3, returnLineIndex):
        line = code[i]

        ret = re.search(FIXED_STR_FUNCHEADER_CONTINUED, line)
        if ret == None or not check62Column( line ):

            ReadLineNum = i + 1

            #print('【関数ヘッダ】フォーマット誤り')
            writeViolation( VIOLATION_TYPE_FUNCHEADER, 'フォーマット誤り', '')
            ##print('対象行=', line)


    #リターン行
    line = code[returnLineIndex]

    ret = re.search(FIXED_STR_FUNCHEADER_RETURN, line)
    if ret == None or not check62Column( line ):

        ReadLineNum = returnLineIndex + 1

        #print('【関数ヘッダ】フォーマット誤り')
        writeViolation( VIOLATION_TYPE_FUNCHEADER, 'フォーマット誤り', '')
        ##print('対象行=', line)

    #リターン行の続き
    for i in range(returnLineIndex + 1, endPos):
        line = code[i]

        ret = re.search(FIXED_STR_FUNCHEADER_CONTINUED, line)
        if ret == None or not check62Column( line ):

            ReadLineNum = i + 1

            #print('【関数ヘッダ】フォーマット誤り')
            writeViolation( VIOLATION_TYPE_FUNCHEADER, 'フォーマット誤り', '')
            ##print('対象行=', line)

    #最終行
    line = code[endPos]
    if line != FIXED_STR_COMMON:

        ReadLineNum = endPos + 1

        #print('【関数ヘッダ】フォーマット誤り')
        writeViolation( VIOLATION_TYPE_FUNCHEADER, 'フォーマット誤り', '')
        ##print('対象行=', line)

    return

#--------------------------
# 関数ヘッダの検証
#--------------------------
def verifyFunctionHeader( code ):

    #1行ずつ読み込み
    for i, line in enumerate(code):

        #行種別を取得
        linekind = getLineKind(line)

        #関数定義の場合
        if linekind == LINEKIND.FUNC_DEFINITION:

            # print('関数ヘッダの検証')
            # print(line)

            #一番先頭の関数定義行を保持していなければ、保持する
            global FirstFuncDefinition
            if FirstFuncDefinition == 0:
                FirstFuncDefinition = i

            #初期化
            flg = False             #ヘッダ下部が見つかれば、Trueにする
            startPos = 0            #ヘッダ開始行
            endPos   = 0            #ヘッダ最終行

            #main定義の上の行から、ファイルの先頭へ向かって関数ヘッダの範囲を確認
            for j in reversed( range( 0, i ) ):
                #ヘッダの始まりと終わりは、「/**」で判定   ※これさえないと破綻する。流石に書いてくれると信じている
                if '/**' in code[j]:
                    if flg:
                        #ヘッダ上部発見
                        startPos = j
                        break
                    else:
                        #ヘッダ下部発見
                        endPos = j
                        flg = True

            #関数ヘッダ判定
            checkFuncHeader( startPos, endPos, code )


#--------------------------
# 関数内の宣言コメントの検証
# ・「/* INTERNAL DATA    */」
# ・「/* PROCESS          */」
#--------------------------
def verifyFunctionComment( code ):

    #関数定義-見つけたら、True
    functionDefinition = False

    #関数定義行
    funcName = ''

    #宣言コメント-見つけたら、True
    InternalFlg = False
    processFlg  = False

    #変数定義
    variableFlg = False

    #1行ずつ読み込み
    for i, line in enumerate(code):

        linekind = getLineKind(line)

        #関数定義の場合
        if linekind == LINEKIND.FUNC_DEFINITION:

            #2つ目以降の関数定義なら、その前の関数内に宣言があるかチェック
            if functionDefinition:
                checkDefinitionCommentInFunc(variableFlg, InternalFlg, processFlg, funcName)

            #フラグ更新
            functionDefinition = True

            #変数定義行の発見フラグをクリア
            variableFlg = False

            #関数定義行を保持
            funcName = line

        #関数定義発見中
        if functionDefinition:

            #変数定義行あり
            if linekind == LINEKIND.VARIABLE:
                variableFlg = True

            #「INTERNAL」発見
            if DECLARATION_INTERNAL in line:
                InternalFlg = True

            #「PROCESS」発見
            if DECLARATION_PROCESS in line:
                processFlg = True

    #ファイル最後の関数定義内をチェック
    if functionDefinition:
        checkDefinitionCommentInFunc(variableFlg, InternalFlg, processFlg, funcName)

    return

#--------------------------
# 関数内の宣言コメントチェック
#--------------------------
def checkDefinitionCommentInFunc( variableFlg, InternalFlg, processFlg, funcName ):

    #変数定義はあるが、「INTERNAL DATA」がない場合
    if (variableFlg) and (not InternalFlg) :
        #print('【関数内の記述】' + funcName + '内に、「INTERNAL DATA」がない or 記述ミス')
        writeViolation( VIOLATION_TYPE_IN_FUNCTION, funcName + '内に、「/* INTERNAL DATA */」がない or 記述ミス', '')

    #「PROCESS」なし
    if not processFlg:
        #print('【関数内の記述】' + funcName + '内に、「PROCESS」がない or 記述ミス')
        writeViolation( VIOLATION_TYPE_IN_FUNCTION, funcName + '内に、「/* PROCESS */」がない or 記述ミス', '')

    return

#--------------------------
# 各種データをクリアする
#   同ファイル内で複数関数がある場合のクリア処理
#--------------------------
def clearData( lineKind ):

    if lineKind == LINEKIND.FUNC_DEFINITION:
        #-- 関数定義の行 --#

        #前回位置をクリア
        global PreVar1stPos
        PreVar1stPos = 0

        global PreParameterPos
        PreParameterPos = 0

    return

#--------------------------
# 文字コード取得
#--------------------------
#def detect_character_code(fileName):
#    file = glob.glob(fileName)
#
#    files_code_dic
#    detector = UniversalDetector()
#    with open(file, 'rb') as f:
#        detector.reset()
#        for line in f.readlines():
#            detector.feed(line)
#            if detector.done:
#                break
#        detector.close()
#        files_code_dic = detector.result['encoding']
#    return files_code_dic


#--------------------------
# ファイル読み込み
#--------------------------
def readFile(fileName):
    #fileObj = open('hot506_test.c', 'r')
    #fileObj = open('hot506_test_tmp.c', 'r')  #★存在しない場合の対応が必要
    #fileObj = open('hot601_196_川口.c', 'r')  #★存在しない場合の対応が必要
    #fileObj = open('hot601_tmp.c', 'r')  #★存在しない場合の対応が必要
    #fileObj = open('sample.c', 'r')  #★存在しない場合の対応が必要

    #-------------------------------
    # 検証対象のファイルをコンソールに出力
    #-------------------------------
    print('')
    print('==================================')
    print(fileName)
    print('==================================')

    #-------------------------------
    #ファイル内のコードを配列で取得
    #-------------------------------
    #UFT-8
    fileObj = open(fileName, 'r', encoding="utf-8")
    #SJIS
    #fileObj = open(fileName, 'r')
    code    = fileObj.readlines()

    # 判定中のライン行目
    global ReadLineNum
    # ファイル内行数（EOF が2行目先頭にある場合、「1」を保持する）
    global LineNum
    LineNum = len(code)

    #各行内の改行を削除し、それを保持する
    for i, line in enumerate(code):
        # 最後の行に改行がなければ、違反
        # しょうがないので、ここでチェック
        if i == (LineNum - 1):
            ReadLineNum = i + 1
            checkEOF(line)

        code[i] = line.replace( LINEFEED_CODE, '' )

    #行数最大Index
    lineMaxIndex = LineNum - 1
    #前回行
    preLine = ''

    #-------------------------------
    # 関数ヘッダ検証（独立して検証）
    #-------------------------------
    verifyFunctionHeader( code )
    # read行数リセット
    ReadLineNum = 0

    #-------------------------------
    # 関数内の宣言コメントの検証（独立して検証）
    #-------------------------------
    verifyFunctionComment( code )
    # read行数リセット
    ReadLineNum = 0

    #-------------------------------
    # 規約の検証
    #-------------------------------
    #1行ずつ読み込み
    for i, line in enumerate(code):

        #判定行数を更新
        ReadLineNum = ReadLineNum + 1

        #最後のIndexでなければ、次の行も取得
        if i < lineMaxIndex:
            nextLine = code[i + 1]
        else:
            #最後の行の次の行は空
            nextLine = ''

        #print(line)
        #print(countLine(line))

        #文の種別を取得
        lineKind = getLineKind(line)

        # print(line)
        # print(getLineKindStr(lineKind))
        # print("----------------------------")

        # print(line)
        # print("種別=" + getLineKindStr(lineKind))

        #クリア
        clearData(lineKind)

        #検証：各種ヘッダ
        verifyHeader(line, preLine, lineKind)

        #検証：コメント
        verifyComment(line, preLine, lineKind)

        #検証：関数外情報
        verifyOutsideFunc(line, preLine, nextLine, lineKind)

        #検証：出力メッセージ
        verifyOutputMessage(line, lineKind)

        #検証：「2章. 関数の記述」
        verifyFunction(line, preLine, nextLine, lineKind)

        #検証：「3章. 識別子の定義」
        verifyIdentifier(line, preLine, lineKind)

        #検証：「5章. 文」
        verifySentence(line, preLine, lineKind)

        #前回行として保持
        preLine = line

    #ファイルクローズ
    fileObj.close()

    # コンソール上で空行を空ける
    print('')

#--------------------------
# メイン処理
#--------------------------
def main():

    # 動作環境の取得
    global OSKind
    OSKind = getOSInformation()

    # 検証対象のフォルダ
    verifyTargetFolder = ''

    #----------------------------
    # Windows専用処理
    #----------------------------
    if OSKind == OS_WINDOWS:
        # Windows専用処理
        
        # フォルダ指定ウインドウ生成
        window = OpenWindow()
        # Excel生成
        createExcel(window.input)

        # 検証対象のフォルダ
        verifyTargetFolder = "./" + window.input + "/*"

    else:
        # Linux専用処理
        # 検証対象のフォルダを本プログラムのpathにする
        verifyTargetFolder = "./*"

    #----------------------------
    # ファイルread
    #----------------------------
    #指定フォルダのファイル読み込み
    files = glob.glob( verifyTargetFolder )
    for file in files:
        # 参考
        # file = 「./test\hot506.c」という形になる（Windowsの場合） --#
        # !ファイル名の前の「/」が「\」になる点に注意! --#

        # ファイル名のみ取得
        fileName = getFileName( file )

        #c,hファイルのみ検証対象とする
        ret = re.search( '\.c$|\.h$', file )
        if ret == None:
            continue

        #「修正前」のワードが入ったファイルは対象外
        ret = re.search( '修正前', file )
        if ret != None:
            continue

        #対象ファイルを書き込み
        writeVerifyFile(fileName)

        #ファイル名のフォーマットチェック
        ret = verifyFileName(fileName)
        if not ret:
            #のちの検証でエラーが出るようになるため、検証対象外とする
            #continue
            pass

        #検証中ファイルの保持
        global FileName
        FileName = fileName

        #記述開始位置検証変数を初期化
        global PreDefine1stPos
        global PreDefine2ndPos
        global PreExternVarPos
        global PreVar1stPos
        global PreMember1stPos
        global PreParameterPos
        global StructReadFLg
        global StructDeclarationFLg
        PreDefine1stPos = 0
        PreDefine2ndPos = 0
        PreExternVarPos = 0
        PreVar1stPos    = 0
        PreMember1stPos = 0
        PreParameterPos = 0
        StructReadFLg = False
        StructDeclarationFLg = False

        # 表示メッセージ管理インスタンスを生成
        global DisplayMsgManager
        DisplayMsgManager = DisplayMessageManager(fileName)

        # ファイル読み込み
        readFile(file)

        # 表示メッセージの検証結果を出力
        writeViolationDisplayMessage()


#--------------
# 動作確認用
#--------------
def test():

    #「;」2つにないか
    #ret = 'aaa;bbb;ccc'.split(';')
    #print( len( ret ) )

    str = '/*  問題番号    ： 第５章  問題６                           */'
    ret = re.search('\/\*  問題番号    ： 第[０-９]章  問題[０-９]                           \*\/', str)

    #if ret:
        #print('あり')
    #else:
        #print('なし')

    '''
    m = re.match(r"(\d+)\.(\d+)", "11.22")
    if m:
        print(m.groups())
        print(len( m.groups() ))

    m = re.match(r"(\d+)=", "11=22")
    if m:
        #print('0--------')
        print(m.groups())
        print(len( m.groups() ))
    '''
    m = re.match('(.+[^<])=(.+)', "AAA=BBB<=CCC>=DDD==EEE")
    if m:
        #print('2--------')
        print(m.groups())
        print(len( m.groups() ))
    m = re.match('(.+[^<])=(.+)', "AAA=BBB<=CCC")
    if m:
        #print('22--------')
        print(m.groups())
        print(len( m.groups() ))
    m = re.match('(.+)=(.+)', "AAA=BBB<=CCC")
    if m:
        #print('222--------')
        print(m.groups())
        print(len( m.groups() ))
    m = re.findall('.=.', "AAA=BBB<=CCC")
    if m:
        #print('2222--------')
        print( m )
        print( len(m) )
    m = re.findall('[^<>=!]=[^=]', "AAA=BBB<=CCC")
    if m:
        #print('AAAA--------')
        print( m )
        print( len(m) )

    m = re.findall('[^<>=!]=[^=]', "AAA=BBB<=CCC>=DDD==EEE=FFF")
    if m:
        #print('BBBB--------')
        print( m )
        print( len(m) )

    m = re.findall('<=', "AAA=BBB<=CCC>=DDD==EEE<=FFF")
    if m:
        #print('CCCC--------')
        print( m )
        print( len(m) )

    m = re.findall('[^<>=!]=[^=]', "AAA&&BBB&CCC&&DDD")
    if m:
        #print('DDDD--------')
        print( m )
        print( len(m) )

    m = re.findall('<<', "AAA<<BBB<<CCC<=DDD")
    if m:
        #print('EEEE--------')
        print( m )
        print( len(m) )

    m = re.findall('[^<]<[^<=]', "AAA<<BBB<<CCC<=DDD<EEE<FFF<")
    if m:
        #print('FFFF--------')
        print( m )
        print( len(m) )

    m = re.findall('[^ ] < [^ ]', "AAA<<BBB<<CCC<=DDD<EEE<FFF < GGG  <  HHH <")
    if m:
        #print('GGGG--------')
        print( m )
        print( len(m) )

    ret = re.search('[=<>!\-\+]', "=")
    if ret:
        print("★＋あり")
    else:
        print("★＋なし")

    ret = re.search('[=<>!\-\+]', "-")
    if ret:
        print("★-あり")
    else:
        print("★-なし")

    if '"' == '"':
        print("aaaa")
    else:
        print("bbbb")

    if ('a' + 'b') == "ab":
        print("連結テスト")

    ret = re.search('[=<>!&|\-\+]', "|")
    if ret:
        print("★|あり")
    else:
        print("★|なし")

    ret = re.search('[|]', "aaa|aaaa")
    if ret:
        print("★|あり2")
    else:
        print("★|なし2")

    ret = re.search('[=<>!&|\-\+]', "aaa|bbb")
    if ret:
        print("★|あり3")
    else:
        print("★|なし3")

    '''
    m = re.match('(.+)[^<]=(.+)', "AAA=BBB<=CCC")
    if m:
        #print('3--------')
        print(m.groups())
        print(len( m.groups() ))

    m = re.match('(.+[^=<>!])=(.+[^=])', "a = b <= c == d >= e != f")
    if m:
        #print('11-------')
        print(m.groups())
        print(len( m.groups() ))

    m = re.match(r"([^=<>!])=([^=])", "for (Countup = 2 ; Countup <= InputNumber ; Countup++)")
    if m:
        #print('1-------')
        print(m.groups())
        print(len( m.groups() ))

    m = re.match(r"=", "for (Countup = 2 ; Countup <= InputNumber ; Countup++)")
    if m:
        #print('2--------')
        print(m.groups())
        print(len( m.groups() ))
    '''

    pass


#--------------------------
# 実行
#--------------------------
main()
