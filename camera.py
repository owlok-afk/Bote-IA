import cv2
import time
import os

SAVE_PATH = "frame.jpg"

def hay_objeto(frame,fondo):

    diff=cv2.absdiff(frame,fondo)
    gray=cv2.cvtColor(diff,cv2.COLOR_BGR2GRAY)
    _,th=cv2.threshold(gray,25,255,cv2.THRESH_BINARY)

    return th.sum()>3000000


cap=cv2.VideoCapture(0,cv2.CAP_DSHOW)

cap.set(cv2.CAP_PROP_FRAME_WIDTH,640)
cap.set(cv2.CAP_PROP_FRAME_HEIGHT,480)

time.sleep(2)

ret,fondo=cap.read()

cooldown=False

print("📷 Camara lista")

while True:

    ret,frame=cap.read()
    if not ret:
        continue

    cv2.imshow("Camara IA",frame)

    if not cooldown and hay_objeto(frame,fondo):

        print("Objeto detectado")

        cv2.imwrite(SAVE_PATH,frame)

        cooldown=True
        time.sleep(5)
        cooldown=False

    if cv2.waitKey(1)==27:
        break

cap.release()
cv2.destroyAllWindows()