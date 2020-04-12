import subprocess
import diff_exporter
import shutil
import os
import re

def read_command_file(command_filepath):
    with open(command_filepath, 'r') as f:
        lines = f.readlines()
    
    # コメント行削除、空白行削除
    lines = [s.rstrip() for s in lines if s[0] is not '#']
    lines = [s for s in lines if len(s) > 0]

    n = len(lines)
    savedirs = [lines[i] for i in range(0, n, 2)]
    shells = [lines[i] for i in range(1, n, 2)]

    return savedirs, shells    

def is_contain_error_string(lines, target_str):
    ret = False
    for line in lines:
        if target_str in line:
            ret = True
            break
    return ret

def execute_commands_and_get_evidence(execute_root_dir, command_file_path, output_root_dir=None, copy_arg_inputfile=True):
    abs_execute_root_dir = os.path.abspath(execute_root_dir)
    print('\n------Target dir: {}------'.format(abs_execute_root_dir))

    # コマンドファイル解析
    savedirs, shells = read_command_file(command_file_path)
    
    # 出力先設定
    if output_root_dir is None:
        output_root_dir = os.getcwd()
        savedirs = [os.path.abspath(s) for s in savedirs]
    else:
        output_root_dir = os.path.abspath(output_root_dir)
        os.makedirs(output_root_dir, exist_ok=True)
        savedirs = [os.path.abspath(os.path.join(output_root_dir, s)) for s in savedirs]

    # チェックポイント作成
    check_point_dir = os.path.join(output_root_dir, '__diff_check_point1')
    diff_exporter.create_check_point(abs_execute_root_dir, save_dir=check_point_dir)
    print('')

    # コマンド実行・エビデンス取得
    error_dirs = []
    os.chdir(abs_execute_root_dir)
    for n, (savedir, shell) in enumerate(zip(savedirs, shells)):
        print('*** Command: {0}/{1} {2}'.format(n+1,len(shells), shell))
        print('    Savedir: {0}'.format(savedir))
        # 保存先作成
        os.makedirs(savedir, exist_ok=True)
        
        # コマンド保存
        with open(os.path.join(savedir, 'command.txt'), 'w', encoding='utf-8') as f:
            f.write(shell)

        # コマンド実行
        log_path = os.path.join(savedir, 'console.txt')
        std_output = ' > {} 2>&1'.format(log_path)
        subprocess.call(shell + std_output, shell=True)

        print('--- Get diff ---')
        # コマンド実行前後の差分コピー
        diff_exporter.output_changed_files(abs_execute_root_dir, savedir, checkpoint_dir=check_point_dir)

        # コマンドラインの入力ファイルをコピー
        if copy_arg_inputfile:
            files = get_command_input_filepath(shell)
            if len(files) > 0:
                save_inputfile_dir = os.path.join(savedir, '_input_files')
                os.makedirs(save_inputfile_dir, exist_ok=True)
                [shutil.copy(p, os.path.join(save_inputfile_dir, os.path.basename(p))) for p in files]
        
        with open(log_path, 'r') as f:
            logs = f.readlines()

        # コンソール内のエラーメッセージチェック
        print('--- Check contain error ---')
        error_str = 'Traceback'
        if is_contain_error_string(logs, error_str):
            print('this executing contain: {}'.format(error_str))
            error_dirs.append(savedir)
        else:
            print('no errors')

        print('--- End. ---')
        print('')
    
    print('-----Complete.-----')
    print('Error executes savedir: {}'.format(error_dirs))

def get_command_input_filepath(command, get_abs=True):
    # コマンド引数にファイルパスがあれば取得する

    # スプリクト以外のコマンド引数を抽出
    pattern = r'((?:^python\d*|^py) \S*) (.*)'
    _args = re.match(pattern, command)
    _args = _args.groups()[-1]
    args = _args.split(' ')

    # ファイルならリストに追加
    input_files = [arg for arg in args if os.path.isfile(arg)]

    if get_abs:
        input_files = [os.path.abspath(p) for p in input_files]

    return input_files

if __name__ == "__main__":

    import argparse, textwrap

    parser = argparse.ArgumentParser(
        formatter_class=argparse.RawTextHelpFormatter,
        description=\
            textwrap.dedent('''\
                エビデンス一括取得スプリクト。
                ディレクトリ下を監視し、コマンド実行前後で更新日時に変更があったファイルを
                ディレクトリ構造ごとコピーする。

                固定出力ファイル:
                    console.txt: 標準出力と標準エラー出力
                    command.txt: コマンド
                    _input_files/*: コマンドラインに引数指定したファイル
            '''
        ))

    parser.add_argument('execute_root_dir', help='コマンドを実行するルートディレクトリ(監視対象)')
    parser.add_argument('commands', 
                help= textwrap.dedent('''\
                    出力ディレクトリと実行コマンドを記載したファイル。
                    以下の形式で記載する。
                    空白行可。#でコメント行。

                        出力先ディレクトリ1
                        実行コマンド1
                        出力先ディレクトリ2
                        実行コマンド2
                        ：
                '''))
    parser.add_argument('-o', '--output_root_dir', help='出力先のルートディレクトリ')
    args = parser.parse_args()
    
    execute_root_dir = args.execute_root_dir
    commands = args.commands
    output_root_dir = args.output_root_dir
    
    # if execute_root_dir.endswith('/'):
    #     execute_root_dir = execute_root_dir[:-1]
    #     print(execute_root_dir)

    execute_commands_and_get_evidence(execute_root_dir, commands, output_root_dir=output_root_dir, copy_arg_inputfile=True))
