'''
Created on Mar 6, 2014

@author: ruicovelo
'''
from tempfile import mkstemp
from shutil import move
from os import path


#TODO: make this abstract?
class FileExport(object):
    '''
    Parent class for all file classes like qif and csv files
    '''

    def __init__(self,file_path):
        self.file_path = file_path
        
    def _create_line(self,transaction):
        return str(transaction)
 
    def save_transactions(self,transactions):
        self._save_transactions(transactions, self.file_path)
        
    def _save_transactions(self,transactions,file_path):
        self._file_handle = open(file_path,"w")
        self._write_transactions(transactions)
        self._file_handle.close()

    def _write_transactions(self,transactions):
        for transaction in transactions:
            self._file_handle.write(self._create_line(transaction)+"\n")
    
    def append_transactions_to_end(self,transactions):
        self._file_handle = open(self.file_path,"a")
        self._write_transactions(transactions)
        self._file_handle.close()
        
    def append_transactions_to_start(self,transactions):
        if not path.exists(self.file_path):
            return self.save_transactions(transactions)
        temp_file_tuple = mkstemp()
        self._save_transactions(transactions, temp_file_tuple[1])
        temp_file_handle = open(temp_file_tuple[1],"a")
        file_handle = open(self.file_path,"r")
        # reading one line at a time
        # file might be big - did not test readlines though...
        line = file_handle.readline()
        while line:
            temp_file_handle.write(line)
            line = file_handle.readline()
        file_handle.close()
        temp_file_handle.close()
        move(temp_file_tuple[1],self.file_path)
        
