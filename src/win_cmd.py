import ctypes

class Console:
    __kernel32 = ctypes.windll.kernel32
    __ENABLE_ECHO_INPUT = 0x0004
    __ENABLE_EXTENDED_FLAGS = 0x0080
    __ENABLE_INSERT_MODE = 0x0020
    __ENABLE_LINE_INPUT = 0x0002
    __ENABLE_MOUSE_INPUT = 0x0010
    __ENABLE_PROCESSED_INPUT = 0x0001
    __ENABLE_QUICK_EDIT_MODE = 0x0040
    __ENABLE_WINDOW_INPUT = 0x0008
    __ENABLE_VIRTUAL_TERMINAL_INPUT = 0x0200
    __DEFAULT_FLAGS = [0x0080, 0x0002, 0x0040, 0x0001, 0x0010, 0x0008, 0x0004, 0x0020]
    __CONIN = -10
    __ACQUIRE = 0
    __RELEASE = 1

    def __gen_mask(enable, *flags):
        mask = 0x0000
        for f in Console.__DEFAULT_FLAGS:
            if not enable and f not in flags:
                mask |= f
            elif enable:
                mask |= f
        return mask
    
    @staticmethod
    def disable_quick_edit():
        Console.__set_lock(Console.__ACQUIRE, Console.__ENABLE_QUICK_EDIT_MODE)
    
    @staticmethod
    def enable_quick_edit():
        Console.__set_lock(Console.__RELEASE, Console.__ENABLE_QUICK_EDIT_MODE)
    
    def __set_lock(mode, option):
        Console.__kernel32.SetConsoleMode(Console.__kernel32.GetStdHandle(Console.__CONIN),\
            Console.__gen_mask(mode, option))