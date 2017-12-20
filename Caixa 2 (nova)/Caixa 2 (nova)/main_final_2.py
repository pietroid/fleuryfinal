from __future__ import division
import kivy
import os

from kivy.app import App
from kivy.uix.screenmanager import ScreenManager,Screen
from kivy.lang import Builder
from kivy.properties import StringProperty
from kivy.core.window import Window
from kivy.core.text import LabelBase
from kivy.core.window import Window
import threading
import numpy as np
import cv2
from picamera.array import PiRGBArray
from picamera import PiCamera
import time
import RPi.GPIO as gpio
  
gpioW1=16 #luz de fundo
gpioW2=20 #luz branca intensa
gpioR=19
gpioG=26

awb_gains_default=(419/256,55/32)

gpio.setmode(gpio.BCM)
gpio.setup(gpioW1,gpio.OUT)
gpio.setup(gpioW2,gpio.OUT)
gpio.setup(gpioR,gpio.OUT)
gpio.setup(gpioG,gpio.OUT)

gpio.output(gpioW1,gpio.HIGH)
gpio.output(gpioW2,gpio.LOW)
gpio.output(gpioR,gpio.LOW)
gpio.output(gpioG,gpio.LOW)


fileW=open('coresW.txt','w')
fileR=open('coresR.txt','w')
fileG=open('coresG.txt','w')


def changeStatus(status):
	tela=screen_manager.get_screen('tela_medicao')
	texto_principal=tela.ids.texto_principal
        texto_aux=tela.ids.texto_aux
        texto_aux2=tela.ids.texto_aux2
        if(status=='inicial'):
                texto_principal.text="NENHUM TUBO INSERIDO"
                texto_aux.text="AGUARDANDO TUBO..."
                texto_aux2.text=""
                texto_aux.color=(1,1,1,1)
                texto_principal.pos_hint= {'y':0.25}
                texto_aux.pos_hint= {'y':0}
        if(status=='invertido'):
                texto_principal.text="TUBO DETECTADO"
                texto_aux.text="TUBO INVERTIDO"
                texto_aux2.text="GIRE O TUBO APROXIMADAMENTE 180 GRAUS"
                texto_principal.pos_hint= {'y':0.25}
                texto_aux.pos_hint= {'y':0}
                texto_aux2.pos_hint= {'y':-0.15}
                texto_aux.color=(1,0,0,1)
                texto_aux2.color=(1,1,1,1)
                texto_aux2.font_size="15sp"
        if(status=='ajuste'):
                texto_principal.text="TUBO DETECTADO"
                texto_aux.text="CENTRALIZE A AMOSTRA"
                texto_aux2.text=""
                texto_principal.pos_hint= {'y':0.25}
                texto_aux.pos_hint= {'y':0}
                texto_aux2.pos_hint= {'y':-0.15}
                texto_aux.color=(1,1,1,1)
                texto_aux2.color=(1,1,1,1)
        if(status=='medicao'):
                texto_principal.text="EFETUANDO MEDICAO"
                texto_aux.text="NAO MOVA O TUBO"
                texto_aux2.text=""
                texto_principal.pos_hint= {'y':0.25}
                texto_aux.pos_hint= {'y':0}
                texto_aux2.pos_hint= {'y':-0.15}
                texto_aux.color=(1,0,0,1)
                texto_aux2.color=(1,1,1,1)

        if(status=='medido'):
                texto_principal.text="TUBO MEDIDO"
                texto_aux.text="INDICE"
                texto_aux2.text="70"
                texto_aux2.font_size="60sp"
                texto_principal.pos_hint= {'y':0.25}
                texto_aux.pos_hint= {'y':0}
                texto_aux2.pos_hint= {'y':-0.2}
                texto_aux.color=(0,0,1,1)
                texto_aux2.color=(0,0,1,1)		

def measureCamera():
        # initialize the camera and grab a reference to the raw camera capture
        camera = PiCamera()
        camera.resolution = (320, 240)
        camera.framerate = 10
        camera.awb_mode='off'
        camera.shutter_speed=5000*4
        camera.awb_gains=awb_gains_default
        rawCapture = PiRGBArray(camera, size=(320, 240))

        # allow the camera to warmup
        time.sleep(0.1)

        tubo_inserido=False
        amostra_detectada=False
        baricentro_y_ant=-1
        a=0
        v_min_ant=100
        time_c=0
        counter=0
        def captura(luz):
            gpio.output(gpioW1,gpio.LOW)
            gpio.output(gpioW2,gpio.LOW)
            gpio.output(gpioR,gpio.LOW)
            gpio.output(gpioG,gpio.LOW)
            if(luz=='R'):
                gpio.output(gpioR,gpio.HIGH)
                awbgains=(65/128,175/64)
            elif(luz=='G'):
                gpio.output(gpioG,gpio.HIGH)
                awbgains=(417/256,449/256)
            else:
                awbgains=(417/256,449/256)
                gpio.output(gpioW2,gpio.HIGH)
            camera.shutter_speed=5284*4
            camera.iso=10
            camera.awb_gains=awbgains
            time.sleep(0.1)
            raw_output = PiRGBArray(camera)
            camera.capture(raw_output, 'bgr')
            """print(camera.awb_gains)
            print(camera.analog_gain)
            print(camera.digital_gain)"""
            output=raw_output.array
            return output
        # capture frames from the camera
        for frame in camera.capture_continuous(rawCapture, format="bgr", use_video_port=True):
            # grab the raw NumPy array representing the image, then initialize the timestamp
            # and occupied/unoccupied text
            image = frame.array 
            crop=image[35:196,153:153+16]
            
            #converte no espaco hsv
            hsv = cv2.cvtColor(crop, cv2.COLOR_BGR2HSV)

            count_amostra=0
            baricentro_y=0
            baricentro_x=0
            points=0
            average_brightness=0
            v_min=100
            for i in range(0,len(crop)):
                for j in range(0,len(crop[0])):
                    h=hsv[i][j][0]*360/179
                    s=hsv[i][j][1]*100/255
                    v=hsv[i][j][2]*100/255
                    if(i>70 and j>5 and j<9):
                        if(v<v_min):
                            v_min=v
                    #se nao for escuro
                    if(h<40 or h>340):
                        if(s>50):
                            #se saturacao eh maior q um valor, isto e, se for colorido, eh amostra
                            amostra=True
                            
                        else:
                            amostra=False
                    else:
                        amostra=False
                    
                    #conta os pixels por linha q eh de amostra
                    if(amostra):
                        count_amostra+=1
                        baricentro_x+=j
                        baricentro_y+=i
                        
            if(count_amostra==0):
                amostra_detectada=False
                baricentro_y=-1    
            else:
                baricentro_x=baricentro_x/count_amostra
                baricentro_y=baricentro_y/count_amostra
                if(abs(baricentro_y_ant-baricentro_y)<2 and baricentro_y>0):
                    amostra_detectada=True
                baricentro_y_ant=baricentro_y 
            
            if(time_c>=2):
                time_c=0
                tubo_inserido=v_min_ant<90 and v_min<90
                v_min_ant=v_min
            else:
                time_c+=1
                
            
            if(tubo_inserido):
                if(status!='medido'):
                    if(amostra_detectada):
                        if(baricentro_x>4 and baricentro_x<12):
                            status='medicao'
                        else:
                            status='ajuste'
                    else:
                        status='invertido'
            else:
                status='inicial'
                
            changeStatus(status)
            if(status=='medicao'):
                outputW=captura('W')
                outputR=captura('R')
                outputG=captura('G')
                gpio.output(gpioW1,gpio.HIGH)
                gpio.output(gpioW2,gpio.LOW)
                gpio.output(gpioR,gpio.LOW)
                gpio.output(gpioG,gpio.LOW)
                crop=outputW[35:196,153:153+16]
                cropR=outputR[35:196,153:153+16]
                cropG=outputG[35:196,153:153+16]

                process=np.zeros((len(crop),len(crop[0]),3)).astype(np.uint8)
            
                hsv = cv2.cvtColor(crop, cv2.COLOR_BGR2HSV)

                #1 filtragem: verifica saturacao
                start_success=-1
                success_sum=0
                factor=0.2
                last_row=0
                for i in range(0,len(crop)):
                    success=0
                    for j in range(0,len(crop[0])):
                        h=hsv[i][j][0]*360/179
                        s=hsv[i][j][1]*100/255
                        v=hsv[i][j][2]*100/255
                        #se matiz esta dentro do vermelho/laranja
                        if(h<35 or h>345):
                            if(s>45):
                                #se saturacao eh maior q um valor, isto e, se for colorido, eh amostra
                                amostra=True
                            else:
                                amostra=False
                        else:
                            amostra=False
                        #conta os pixels por linha q eh de amostra
                        if(amostra):
                            success+=1
                            process[i][j]=hsv[i][j]
                    last_row=i

                    #2 filtragem para descartar os blocos nao conectados
                    if(success>0 and start_success==-1):
                        start_success=i
                    if(start_success>=0):
                        success_sum+=success
                        success_average=success_sum/(i-start_success+1)
                        if(success<factor*success_average and (i-start_success)>10 and success_average>5):
                            process[i]=np.zeros((1,len(crop[0]),3)).astype(np.uint8)
                            break
                color_count=0
                W_average=(0,0,0)
                R_average=(0,0,0)
                G_average=(0,0,0)
                for i in range(0,last_row+1):
                    for j in range(0,len(process[0])):
                        if(not np.array_equal(process[i][j],[0,0,0])):
                            W_average+=crop[i][j]
                            R_average+=cropR[i][j]
                            G_average+=cropG[i][j]
                            color_count+=1
                            
                if(color_count!=0):
                   W_average=W_average/color_count
                   R_average=R_average/color_count
                   G_average=G_average/color_count
                print(W_average)
                fileW.write(str(W_average)+'\n')
                fileR.write(str(R_average)+'\n')
                fileG.write(str(G_average)+'\n')
                
                #funcao da rede neural
                indice=W_average[1]
                
                cv2.imwrite('imageW'+str(counter)+'.png',outputW)
                cv2.imwrite('imageR'+str(counter)+'.png',outputR)
                cv2.imwrite('imageG'+str(counter)+'.png',outputG)
                counter+=1
                
                status='medido'
                changeStatus(status)
                camera.shutter_speed=5000*4
                camera.awb_gains=awb_gains_default
            
           # show the frame
            print(status)
            key=cv2.waitKey(1)&0xFF

            # clear the stream in preparation for the next frame
            rawCapture.truncate(0)

            # if the `q` key was pressed, break from the loop
            if key == ord("q"):
                fileW.close()
                fileG.close()
                fileR.close()
                break



        

Window.fullscreen = True

LabelBase.register(name="keep_calm",fn_regular="KeepCalm-Medium.ttf")

Builder.load_file('main_final.kv')

class TelaMedicao (Screen):
    def initialize(self):
        threading.Thread(target=self.second_thread).start()
    
    def second_thread(self):
        measureCamera()

screen_manager=ScreenManager()

screen_manager.add_widget(TelaMedicao(name='tela_medicao'))

class MainApp(App):
	def build(self):
                screen_manager.get_screen('tela_medicao').initialize()
		return screen_manager

MainApp().run()



