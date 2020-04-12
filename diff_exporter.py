import os
import shutil
import glob
import json


def search_diff(pre_states, current_states):
    '''
    過去vs現在でディレクトリ内を比較し、以下をリストで返す。
        ・更新日時に差分があるファイルパス
        ・新規作成されたディレクトリパス
    '''

    diff_file = []
    diff_dir = []
    for path, mtime in current_states.items():
        if path in pre_states:
            if not pre_states[path] == current_states[path]:
                if os.path.isfile(path):
                    diff_file.append(path)
        else:
            if os.path.isfile(path):
                diff_file.append(path)
            else:
                diff_dir.append(path)

    return diff_file, diff_dir

def get_current_states(target_dir):
    current_dir = os.getcwd()
    os.chdir(target_dir)
    paths = glob.glob('**', recursive=True)
    current_states = {f:os.stat(f).st_mtime for f in paths}
    os.chdir(current_dir)

    return current_states

def get_default_checkpoint_dir(target_dir, make_dir=True):
    output_dir_path = os.path.abspath(os.path.dirname(target_dir))
    save_dir = os.path.join(output_dir_path, '__diff_check_point')
    if make_dir:
        os.makedirs(save_dir, exist_ok=True)

    return save_dir

def get_checkpoint_path(target_dirpath, checkpoint_dir=None):
    file_name = 'check_point_{}.json'.format(os.path.basename(target_dirpath))
    if checkpoint_dir is None:
        checkpoint_dir = get_default_checkpoint_dir(target_dirpath)

    ret_path = os.path.join(checkpoint_dir,file_name)

    return ret_path

def create_check_point(target_dir, save_dir=None):
    current_states = get_current_states(target_dir)
    
    # 状態を保存
    savefile_name = 'check_point_{}.json'.format(os.path.basename(target_dir))

    # 出力先未指定の場合、ターゲットディレクトリの親ディレクトリに出力先作成
    check_point_path = get_checkpoint_path(target_dir, save_dir)
    check_point_dir = os.path.dirname(check_point_path)
    if not os.path.exists(check_point_dir):
        os.makedirs(check_point_dir, exist_ok=True)

    with open(check_point_path, "w", encoding='utf-8') as f:
        json.dump(current_states, f, ensure_ascii=False, indent=4, sort_keys=False, separators=(',', ': '))

    print('  Created check point file.\n  {}'.format(os.path.join(save_dir,savefile_name)))

def load_check_point(target_dir, checkpoint_dir=None):
    check_point_path = get_checkpoint_path(target_dir, checkpoint_dir)
    with open(check_point_path, "r", encoding='utf-8') as f:
        pre_states = json.load(f)

    return pre_states

def update_check_point(states, target_dir, checkpoint_dir):
    check_point_path = get_checkpoint_path(target_dir, checkpoint_dir)
    with open(check_point_path, "w", encoding='utf-8') as f:
        json.dump(states, f, ensure_ascii=False, indent=4, sort_keys=False, separators=(',', ': '))

def output_changed_files(target_dir, output_dir, update_save_point=True, checkpoint_dir=None):
    if not os.path.exists(output_dir):
        os.makedirs(output_dir, exist_ok=True)

    # 絶対パスに変換
    target_dir = os.path.abspath(target_dir)
    output_dir = os.path.abspath(output_dir)

    # --- チェックポイントポイントロード
    pre_states = load_check_point(target_dir, checkpoint_dir=checkpoint_dir)

    # 現在の状態を取得
    curdir = os.getcwd()
    os.chdir(target_dir)
    paths = glob.glob('**', recursive=True)
    current_states = {f:os.stat(f).st_mtime for f in paths}

    # 差分取得
    diff_file, diff_dir = search_diff(pre_states, current_states)
    _diff_file_dirs = set([os.path.dirname(p) for p in diff_file if os.path.isfile(p)])
    diff_file_dirs = [p for p in _diff_file_dirs if p != '']

    print('diff:\nfiles: {}\ndir: {}'.format(diff_file, diff_dir))

    # 差分コピー先のディレクトリ構造を生成
    os.chdir(output_dir)
    [os.makedirs(p, exist_ok=True) for p in diff_file_dirs]
    [os.makedirs(p, exist_ok=True) for p in diff_dir]

    # 差分をコピー
    [shutil.copyfile(os.path.join(target_dir, p), p) for p in diff_file]

    # チェックポイントを更新
    if update_save_point:
        update_check_point(current_states, target_dir, checkpoint_dir=checkpoint_dir)

    os.chdir(curdir)

# if __name__ == "__main__":
#     import argparse
#     parser = argparse.ArgumentParser(
#         formatter_class=argparse.RawDescriptionHelpFormatter,
#         description=\
#         '''
#         ファイル差分検出スプリクト。
#         予めチェックポイントを作成し、チェックポイントと現在での差分を検出し、ファイル出力する。
#         '''
#         )

#     parser.add_argument('dir', help='差分を取るディレクトリ')
#     parser.add_argument('-o', '--output_dir', help='差分を出力するディレクトリ', default=None)
#     parser.add_argument('-u', '--update_check_point', help='チェックポイントの上書き設定', default='t')

#     args = parser.parse_args()

#     update_save_point = args.update_check_point == 't'

#     if not args.output_dir:
#         create_check_point(args.dir)

#     else:
#         output_changed_files(args.dir, args.output_dir, update_save_point)
