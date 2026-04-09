from typing import Literal
from subprocess import run as _run
from colorama import init, Fore as F
from ctypes import windll
from msvcrt import getch

init()

from lib.utils.config import ConfigManager

def create_option(label: str, option_id: str, option_type: str, **kwargs) -> dict:
    option = {'label': label, 'id': str(option_id), 'type': option_type}
    option.update(kwargs)
    return option

class OptionType:
    SUBMENU = 'submenu'
    INPUT   = {'number': 'input_number', 'confirm': 'input_confirm', 'text': 'input_text'}
    ACTION  = 'action'
    TOGGLE  = 'toggle'

class UserInterface:
    def __init__(self, menu_tree: dict):
        self.menu_tree      = menu_tree
        self.current_path   = []
        self.selected_index = 0
        self.index_history  = []
        self.message        = ''
        self._running       = True
    
    def set_title(self, title: str):
        base = "dstvx's SAS:ZA4Tool"
        windll.kernel32.SetConsoleTitleW(f"{base} - {title}")

    def get_current_nodes(self):
        current_nodes = self.menu_tree
        for path_id in self.current_path:
            children = current_nodes.get('children', [])
            if callable(children): children = children()
            
            found = False
            for child in children:
                if child.get('id') == path_id:
                    current_nodes = child
                    found = True
                    break
            if not found: break
        return current_nodes
    
    def get_node_by_id(self, target_id: str):
        if self.menu_tree.get('id') == target_id: return self.menu_tree
            
        current = self.menu_tree
        for path_id in self.current_path:
            children = current.get('children', [])
            if callable(children): children = children()
            
            found_child = False
            for child in children:
                if child.get('id') == target_id: return child
                if child.get('id') == path_id:
                    current = child
                    found_child = True
                    break
            if not found_child: break
        return {}

    def get_node_display(self, node: dict):
        label = node['label']
        if node['type'] == OptionType.INPUT['confirm']: return label
        
        if node['type'] in OptionType.INPUT.values() or node['type'] == OptionType.TOGGLE:
            val = node.get('value')
            if callable(val): val = val()
                
            if node['type'] == OptionType.TOGGLE:
                return f"{label}: [{'✓' if val else '✗'}]"
            else:
                display_val = val if val is not None else (0 if node['type'] == OptionType.INPUT['number'] else '')
                return f"{label}: [{display_val}]"
        return label

    def get_node_icon(self, node: dict):
        if node['type'] == OptionType.SUBMENU: return f'{F.LIGHTCYAN_EX}>'
        if node['type'] in OptionType.INPUT.values(): return f'{F.LIGHTBLUE_EX}*'
        if node['type'] == OptionType.ACTION: return f'{F.LIGHTYELLOW_EX}!'
        if node['type'] == OptionType.TOGGLE: return f'{F.GREEN}v' if node.get('value') else f'{F.RED}x'
        return '-'

    def display_menu(self):
        _run('cls', shell=True)
        with ConfigManager() as config:
            profile = config.data.get('selected_profile', 'None')
            
        print(r'''{}        _______   _____ ____  ___  __________          __
       / __/ _ | / __(_)_  / / _ |/ / /_  __/__  ___  / /
      _\ \/ __ |_\ \_   / /_/ __ /_  _// / / _ \/ _ \/ / 
     /___/_/ |_/___(_) /___/_/ |_|/_/ /_/  \___/\___/_/  
                    {}by{}: {}dstvx{} ver{}: {}1.0.0{}
                 {}Selected Profile: {}{}{}'''.format(
                     F.LIGHTRED_EX, F.CYAN, F.LIGHTWHITE_EX, F.LIGHTGREEN_EX, F.CYAN, F.LIGHTWHITE_EX, F.LIGHTGREEN_EX, F.RESET,
                     F.CYAN, F.LIGHTGREEN_EX, profile, F.RESET
                 ))
        
        cur = self.menu_tree
        for pid in self.current_path:
            for child in cur.get('children', []):
                if child.get('id') == pid:
                    cur = child
                    break

        if self.message: print(f'\n {F.LIGHTWHITE_EX}Message: {self.message}{F.RESET}\n')
        elif 'message' in cur: print(f'\n {F.YELLOW}Message: {cur["message"]}{F.RESET}\n')
        
        if not self.current_path: self.set_title("Main menu")
        else:
            labels = []
            for nid in self.current_path:
                node = self.get_node_by_id(nid)
                if node.get('type') == OptionType.SUBMENU: labels.append(node['label'])
            self.set_title(" > ".join(labels))
        
        nodes = self.get_current_nodes()
        children = nodes.get('children', [])
        if callable(children): children = children()
            
        for i, node in enumerate(children):
            prefix = f'{F.GREEN}>>{F.RESET}' if i == self.selected_index else '  '
            print(f'{prefix} {F.LIGHTWHITE_EX}[{self.get_node_icon(node)}{F.LIGHTWHITE_EX}] {self.get_node_display(node)}{F.RESET}')
        
        print(f"\n{F.LIGHTWHITE_EX}Controls{F.LIGHTGREEN_EX}: "
              f"{F.LIGHTWHITE_EX}[{F.LIGHTBLUE_EX}Up{F.LIGHTWHITE_EX}/{F.LIGHTBLUE_EX}Down{F.LIGHTWHITE_EX}] "
              f"{F.LIGHTGREEN_EX}Navigate {F.LIGHTWHITE_EX}| "
              f"{F.LIGHTWHITE_EX}[{F.LIGHTBLUE_EX}Enter{F.LIGHTWHITE_EX}] "
              f"{F.LIGHTGREEN_EX}Select {F.LIGHTWHITE_EX}| "
              f"{F.LIGHTWHITE_EX}[{F.LIGHTBLUE_EX}Esc{F.LIGHTWHITE_EX}/{F.LIGHTBLUE_EX}b{F.LIGHTWHITE_EX}] "
              f"{F.LIGHTGREEN_EX}Back {F.LIGHTWHITE_EX}| "
              f"{F.LIGHTWHITE_EX}[{F.LIGHTBLUE_EX}q{F.LIGHTWHITE_EX}] "
              f"{F.LIGHTGREEN_EX}Quit{F.RESET}")
            
    def handle_select(self):
        nodes = self.get_current_nodes()
        children = nodes.get('children', [])
        if callable(children): children = children()
        if not children: return
            
        selected_node = children[self.selected_index]
        node_type = selected_node['type']

        if node_type == OptionType.SUBMENU:
            sub_children = selected_node.get('children', [])
            if callable(sub_children): sub_children = sub_children()
            if not sub_children:
                self.message = f"{F.RED}Empty.{F.RESET}"
                return
            self.current_path.append(selected_node['id'])
            self.index_history.append(self.selected_index)
            self.selected_index = 0
            return

        if node_type == OptionType.ACTION:
            if 'action' not in selected_node: return
            self.message = f"{F.YELLOW}Executing...{F.RESET}"
            self.display_menu()
            
            res = selected_node['action']()
            if not isinstance(res, dict):
                self.message = f"{F.GREEN}Done!{F.RESET}"
                return

            self.message = f"{F.RED if res.get('is_error') else F.GREEN}{res.get('message', 'Done!')}{F.RESET}"
            if res.get('command', {}).get('exit'): self._running = False
            return

        if node_type == OptionType.TOGGLE:
            cur_val = selected_node.get('value')
            if callable(cur_val): cur_val = cur_val()
            
            new_val = not bool(cur_val)
            if not callable(selected_node.get('value')): selected_node['value'] = new_val
            selected_node['_last_input'] = new_val
            
            if 'config_key' in selected_node:
                with ConfigManager() as config: config.data[selected_node['config_key']] = new_val
                    
            if 'action' not in selected_node:
                self.message = f"{F.CYAN}Toggled: {'ON' if new_val else 'OFF'}{F.RESET}"
                return

            res = selected_node['action']()
            if not isinstance(res, dict):
                self.message = f"{F.CYAN}Toggled: {'ON' if new_val else 'OFF'}{F.RESET}"
                return

            self.message = f"{F.RED if res.get('is_error') else F.CYAN}{res.get('message', 'Toggled.')}{F.RESET}"
            if res.get('command', {}).get('exit'): self._running = False
            return
        
        if node_type == OptionType.INPUT['number']:
            self.message = f"{F.LIGHTBLUE_EX}Set for: {selected_node['label']}{F.RESET}"
            self.display_menu()
            
            min_v = selected_node.get('range_min')
            max_v = selected_node.get('range_max')
            prompt = 'Value '
            if min_v is not None and max_v is not None: prompt += f'({min_v}-{max_v})'
            try:
                val = int(input(f"{prompt}: "))
            except (ValueError, KeyboardInterrupt):
                self.message = f"{F.RED}Cancelled or Invalid.{F.RESET}"
                return
            if (min_v is not None and val < min_v) or (max_v is not None and val > max_v):
                self.message = f"{F.RED}Out of range.{F.RESET}"
                return

            if not callable(selected_node.get('value')): selected_node['value'] = val
            selected_node['_last_input'] = val
            if 'config_key' in selected_node:
                with ConfigManager() as config: config.data[selected_node['config_key']] = val
            self.message = f"{F.GREEN}Set to: {val}{F.RESET}"
            
            if 'action' in selected_node:
                res = selected_node['action']()
                if isinstance(res, dict):
                    self.message = f"{F.RED if res.get('is_error') else F.GREEN}{res.get('message', self.message)}{F.RESET}"
                    if res.get('command', {}).get('exit'): self._running = False
            return
        
        if node_type == OptionType.INPUT['text']:
            self.message = f"{F.LIGHTBLUE_EX}Enter for: {selected_node['label']}{F.RESET}"
            self.display_menu()
            try:
                val = input('Value: ')
            except KeyboardInterrupt:
                self.message = f"{F.RED}Cancelled.{F.RESET}"
                return
            if not callable(selected_node.get('value')): selected_node['value'] = val
            selected_node['_last_input'] = val
            if 'config_key' in selected_node:
                with ConfigManager() as config: config.data[selected_node['config_key']] = val
            self.message = f"{F.GREEN}Set to: {val}{F.RESET}"
            
            if 'action' in selected_node:
                res = selected_node['action']()
                if isinstance(res, dict):
                    self.message = f"{F.RED if res.get('is_error') else F.GREEN}{res.get('message', self.message)}{F.RESET}"
                    if res.get('command', {}).get('exit'): self._running = False
            return

        if node_type == OptionType.INPUT['confirm']:
            self.message = f"{F.YELLOW}Confirm: {selected_node['label']}{F.RESET}"
            self.display_menu()
            try:
                confirm = input("Proceed? (Y/N): ").strip().lower()
            except KeyboardInterrupt:
                self.message = f"{F.RED}Cancelled{F.RESET}"
                return
                
            if confirm not in ('y', 'yes'):
                self.message = f"{F.RED}Cancelled{F.RESET}"
                return
            self.message = f"{F.GREEN}Confirmed.{F.RESET}"
            if 'action' in selected_node: selected_node['action']()
            return
        self.message = f"{F.RED}Not implemented.{F.RESET}"

    def handle_back(self):
        if self.current_path:
            self.message = ''
            self.current_path.pop()
            self.selected_index = self.index_history.pop() if self.index_history else 0

    def handle_up(self):
        if self.selected_index > 0: self.selected_index -= 1
    
    def handle_down(self):
        nodes = self.get_current_nodes()
        children = nodes.get('children', [])
        if callable(children): children = children()
        if self.selected_index < len(children) - 1: self.selected_index += 1

    def _get_key(self):
        ch = getch()
        if ch == b'\xe0':
            ch2 = getch()
            if ch2 == b'H': return 'up'
            if ch2 == b'P': return 'down'
        elif ch == b'\r': return 'enter'
        elif ch in [b'b', b'\x1b']: return 'b'
        elif ch in [b'q', b'\x03']: return 'q'

    def run(self):
        print('\033[?25l', end='')
        try:
            while self._running:
                self.display_menu()
                try:
                    key = self._get_key()
                except KeyboardInterrupt:
                    break
                    
                if key == 'up': self.handle_up()
                elif key == 'down': self.handle_down()
                elif key == 'enter': self.handle_select()
                elif key == 'b': self.handle_back()
                elif key == 'q': break
        finally: print('\033[?25h', end='')
