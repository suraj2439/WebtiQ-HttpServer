
def handleEncodingPriority(val):
    availableEncodings = ["br","compress", "deflate", "gzip", "exi", "pack200-gzip", 
        "x-compress","x-gzip", "zstd"]
    processedEncodings = {}

    accValues = val.split(",")
    for value in accValues:
        tmpArr = value.split(";", 1)
        if(len(tmpArr) == 2):
            priority = float((tmpArr[1].split("="))[1].strip())
        else:
            priority = 1.0
        if(tmpArr[0] == "*"):
            for enc in availableEncodings:
                if enc not in processedEncodings:
                    processedEncodings[enc] = priority
        else:
            processedEncodings[tmpArr[0]] = priority
    
    result = max(processedEncodings, key = processedEncodings.get)
    if processedEncodings[result] > 0:
        return result
    return None


def handleAcceptContentPriority(val):
    pass