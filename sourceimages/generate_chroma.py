from PIL import Image

width, height = 1920, 1080
image = Image.new("RGB", (width, height))

for x in range(width):
    for y in range(height):
        if y > 535 and y < 545:
            # Make a black stripe in the intersection.
            image.putpixel((x, y), (0, 0, 255))
            continue
        if y > 540:
            if x % 2 == 0:
                image.putpixel((x, y), (255, 0, 0))
            else:
                image.putpixel((x, y), (0, 0, 255))
        else:
            if y % 2 == 0:
                image.putpixel((x, y), (0, 0, 255))            
            else:
                image.putpixel((x, y), (255, 0, 0))

#image.show()
image.save("chromatest_1080.png")