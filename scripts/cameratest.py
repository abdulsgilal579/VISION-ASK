import cv2

def test_camera():
    # 0 = default camera (built-in webcam)
    # Try 1 or 2 if you have multiple cameras
    cap = cv2.VideoCapture(0)

    if not cap.isOpened():
        print("❌ Could not open camera. Try changing index to 1 or 2.")
        return

    print("✅ Camera opened successfully!")
    print("Press Q to quit.")

    while True:
        ret, frame = cap.read()

        if not ret:
            print("❌ Failed to read frame.")
            break

        # Show camera feed in a window
        cv2.imshow("Camera Test", frame)

        # Press Q to quit
        if cv2.waitKey(1) & 0xFF == ord('q'):
            break

    cap.release()
    cv2.destroyAllWindows()
    print("Camera released.")

if __name__ == "__main__":
    test_camera()