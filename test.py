from multiprocessing import Pool
import time


def func(arg):
   time.sleep(0.001)
   print("process order: "+str(arg))
   return arg
if __name__=='__main__':
   proc_pool = Pool(4)
   results = proc_pool.map(func, range(30))
   proc_pool.close()
   proc_pool.join()

   for a in results:
      print("output order"+str(a)) 
