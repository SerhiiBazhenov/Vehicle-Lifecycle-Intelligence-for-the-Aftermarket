import os

adomd_path = r"C:\Program Files\Microsoft.NET\ADOMD.NET\160"
os.environ["PATH"] = adomd_path + ";" + os.environ["PATH"]

import clr

clr.AddReference(
    r"C:\Program Files\Microsoft.NET\ADOMD.NET\160\Microsoft.AnalysisServices.AdomdClient.dll"
)

print("ADOMD loaded successfully")