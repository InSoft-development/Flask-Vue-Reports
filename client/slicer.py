#!/usr/bin/env python3
import sqlite3
import datetime
import time
import csv
import matplotlib.pyplot as plt
import argparse
import pandas as pd
import numpy as np
import traces as tr
import numba
import sqlite3


def parse_args():
    parser = argparse.ArgumentParser(description="dump slices of data from archive")
    parser.add_argument("--delta", "-d", type=int, help="delta between slices in seconds(default 300 sec)", default=300)
    parser.add_argument("--interval", "--time", "-t", nargs=2, required=True, type=datetime.datetime.fromisoformat,
                        help="two timestamps, period, format YYY-MM-DD HH:MM:SS.SSS")
    parser.add_argument("--output", "-o", default="slices.csv", type=str,
                        help="output csv file")
    parser.add_argument("--input", "-i", default="data.sqlite", type=str,
                        help="input sqlite file")

    return parser.parse_args()


# @numba.njit
# def mean5(data, nums):
#     # средние
#     means_for_5 = pd.DataFrame()
#     print("means forming")
#     start_time = time.time()
#     sampling_period = datetime.timedelta(seconds=15)
#     start = datetime.datetime(2021, 6, 1)
#     end = datetime.datetime(2022,10, 30)
#     t = start
#     value_kks = dict.fromkeys(nums + ["timestamp"])
#     for a in value_kks.keys():
#         value_kks[a] = []
#     mean = 0
#     while t < end:
#         t2 = t + sampling_period
#         data_t = data.query("timestamp >= @t and timestamp < @t2")
#         value_kks["timestamp"].append(t2)
#         for k in nums:
#             data_k = data_t[data_t.kks == k]
#             if len(data_k) > 0:
#                 mean = data_k["value"].mean()
#             elif len(value_kks[k]) > 0:
#                 mean = value_kks[k][-1]
#             else:
#                 mean = 0
#             value_kks[k].append(mean)
#         t = t2
#     return value_kks

if __name__ == '__main__':
    args = parse_args()
    delta = datetime.timedelta(seconds=args.delta)
    outfile = args.output
    infile = args.input

    print(args)

    nums = pd.read_csv("kks.csv", header=None)[0].to_list()  # ["20MAD11CY004"] #
    start_date = args.interval[0]  # datetime.datetime(2021, 6, 1)
    end_date = args.interval[1]  # datetime.datetime(2022, 10, 30)

    slices1 = pd.DataFrame({"timestamp": []})
    slices2 = pd.DataFrame({"timestamp": []})

    print("slices forming")
    start_time = time.time()
    for kks in nums:
        print(kks)
        try:
            conn_raw = sqlite3.connect(infile)
            # sql = ("SELECT t as timestamp,val as value, status FROM dynamic_data WHERE id=\"" +
            #    kks + "\" ") #and t > \"" + start_date.isoformat() + "\" and t < \"" +
            #    #end_date.isoformat() + "\"")
            sql = ("SELECT t as timestamp,val as value, status, static_data.name as name "
                   "FROM dynamic_data JOIN static_data ON dynamic_data.id = static_data.id WHERE name=\"" +
                   kks + "\" ")  # and t > \"" + start_date.isoformat() + "\" and t < \"" +
            # end_date.isoformat() + "\"")
            data_column = pd.read_sql(sql, conn_raw, parse_dates=['timestamp'])
            if len(data_column) == 0:
                print("missing data!!")
                data_column = pd.DataFrame([{"timestamp": start_date, "value": 0,"status":"missed"},
                    {"timestamp": end_date, "value": 0,"status":"missed"}])
                with open("failed_kks", "a") as f:
                    f.write(kks+"\n")
            print(data_column[["timestamp", "value"]].values)
            ts1 = tr.TimeSeries(data_column[["timestamp", "value"]].values)
            column1 = ts1.sample(sampling_period=delta,
                           start=start_date,
                           end=end_date,
                           interpolate='previous')
            slices1 = slices1.merge(pd.DataFrame(column1, columns=["timestamp", kks]),
                                  how="outer")

            ts2 = tr.TimeSeries(data_column[["timestamp", "status"]].values)
            column2 = ts2.sample(sampling_period=delta,
                           start=start_date,
                           end=end_date,
                           interpolate='previous')

            slices2 = slices2.merge(pd.DataFrame(column2, columns=["timestamp", kks]),
                                  how="outer")
        except:
            with open("failed_kks", "a") as f:
                f.write(kks+"\n")

    print(time.time() - start_time)
    print(slices1)
    print(slices2)

    slices1.to_csv(outfile, index=False)
    slices2.to_csv(outfile[:-4]+"_status.csv", index=False)
