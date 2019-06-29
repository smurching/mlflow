from collections import defaultdict
import os

import argparse, git, pickle, requests


def format_oneline(commit):
    # TODO: maybe make links to github PRs
    # TODO: support listing multiple authors
    return '- %s (#%d, @%s)' % (commit['title'], commit['pr'], commit['author_github_handle'])


def main():
    parser = argparse.ArgumentParser(
        description="Generate a changelog for the repo from the given previous branch. "
                    "Example usage:\n"
                    " $ git fetch upstream\n"
                    " $ python generate_changelog.py --prev-branch branch-0.9.1 > commits-parsed-0.9.1-master.txt")
    parser.add_argument("--prev-branch", nargs='?', required=True,
                        help="Previous release branch to compare to, e.g. branch-0.8")
    # TODO: why use upstream/master here instead of just master? I guess the upstream is better since it
    # won't have weird local-only changes
    parser.add_argument("--curr-branch", nargs='?', default="upstream/master",
                        help="Current release (candidate) branch to compare to, e.g. branch-0.9. "
                             "Defaults to 'upstream/master'.")
    parser.add_argument("--skip-github", dest="skip_github", const=True, default=False, action='store_const',
                        help="Skip querying github and use the cached commits file.")

    parsed = parser.parse_args()
    prev_branch = parsed.prev_branch
    curr_branch = parsed.curr_branch
    skip_github = parsed.skip_github

    # get the list
    g = git.Git(os.getcwd())
    # TODO: automate `git fetch upstream`
    loginfo = g.log('--left-right', '--graph', '--cherry-pick', '--pretty=format:\'%an\t%s\'',
                    'upstream/'+prev_branch+'...'+curr_branch)

    newlogs = [str(l)[3:-1] for l in loginfo.split("\n") if str.startswith(str(l), '>')]
    #print(len(newlogs))

    prev_branch_for_file = prev_branch.replace("/", ".")
    curr_branch_for_file = curr_branch.replace("/", ".")
    github_cache_file = "commits-%s-%s.pkl" % (prev_branch_for_file, curr_branch_for_file)
    raw_github_cache_file = "raw-commits-%s-%s.pkl" % (prev_branch_for_file, curr_branch_for_file)  # for dev
    if skip_github:
        with open(github_cache_file, "rb") as f:
            commits = pickle.load(f)
        # for development of this script
        with open(raw_github_cache_file, "rb") as f:
            raw_commits = pickle.load(f)
    else:

        # get the github handle from github
        user_name = os.environ.get("GITHUB_USERNAME")
        api_token = os.environ.get("GITHUB_API_TOKEN")
        if user_name is None or api_token is None:
            raise Exception("Must provide Github username & API token via "
                            "'GITHUB_USERNAME' and 'GITHUB_API_TOKEN' environment variables")
        raw_commits = []
        commits = {}
        for log in newlogs:
            [author_name, title] = log.split("\t")
            pr_num_ind = title.rfind('(#')
            if pr_num_ind < 0:
                continue
            pr_num = int(title[pr_num_ind+2:-1])
            print("...Sending github request for PR %d" % pr_num)
            r = requests.get('https://api.github.com/repos/mlflow/mlflow/pulls/%d' % pr_num,
                             auth=(user_name, api_token))
            rjson = r.json()
            raw_commits.append(rjson)

            github_handle = rjson['user']['login']
            commits[pr_num] = {
                'author_name': author_name,
                'title': title[:pr_num_ind-1],
                'pr': pr_num,
                'author_github_handle': github_handle,
            }
        with open(github_cache_file, "wb") as f:
            pickle.dump(commits, f)
        with open(raw_github_cache_file, "wb") as f:
            pickle.dump(raw_commits, f)

    original_info = {}
    if type(commits) is dict:
        original_info = commits
    else:
        # older version of script saved a list instead of a dict
        for commit in commits:
            original_info[commit["pr"]] = commit
    extra_info = {}
    sorted_prs = defaultdict(list)
    multilabel_prs = []
    for rjson in raw_commits:
        pr_num = rjson['number']
        labels = [n for n in [l['name'] for l in rjson['labels']] if n.startswith('rn/')]
        extra_info[pr_num] = {
            'pr': pr_num,
            'labels': labels,
            'body': rjson['body'],
        }
        if len(labels) > 1:
            multilabel_prs.append(pr_num)
        if len(labels) == 0:
            sorted_prs["no-label"].append(pr_num)
        for label in labels:
            sorted_prs[label].append(pr_num)
    for k in sorted_prs.keys():
        assert k in ["rn/feature", "rn/breaking-change", "rn/bug-fix", "rn/documentation", "rn/none", "no-label"], k

    def pr_list_text(categories, title):
        prs = []
        for cat in categories:
            prs += sorted_prs[cat]
        return title + " (%d)\n\n" % len(prs) + \
               "\n".join([format_oneline(original_info[pr_num]) for pr_num in prs]) + "\n"

    # rn/breaking-change
    breaking_text = pr_list_text(["rn/breaking-change"], "Breaking changes:")

    # rn/feature
    feature_text = pr_list_text(["rn/feature"],
                                "Features (to be divided into major and other):")

    # rn/bug-fix, rn/documentation
    bug_doc_text = pr_list_text(["rn/bug-fix", "rn/documentation"],
                                "Bug fixes and documentation updates:")

    # rn/none
    handle_to_prs = defaultdict(list)
    for pr_num in sorted_prs["rn/none"]:
        handle = original_info[pr_num]['author_github_handle']
        handle_to_prs[handle].append("#" + str(pr_num))
    small_list_text = "(" + "; ".join([", ".join(pr_nums + ["@" + handle])
                                       for handle, pr_nums in handle_to_prs.items()]) + ")"
    small_text = "Small bug fixes and doc updates " + \
                 small_list_text + "\n"

    # no label PRs
    no_label_text = pr_list_text("no-label", "The following PRs need to be categorized:")

    # PRs with multiple labels - let the release notes author know
    multiple_text = "** The following PRs were found to have multiple release notes labels: " + \
                    ", ".join([str(pr_num) for pr_num in multilabel_prs]) + "\n"

    # Contributor name list for the blog post
    contributor_text = g.log('--left-right', '--graph', '--cherry-pick', '--pretty=format:%an',
                             'upstream/'+prev_branch+'...'+curr_branch)
    contributors = sorted(set([c[2:] for c in contributor_text.split("\n")]))
    contributor_text = "** For the blog post, the list of contributors: " + \
                       ", ".join(contributors) + "\n"

    text_for_author = "\n".join([breaking_text, feature_text, bug_doc_text, small_text,
                                 no_label_text, multiple_text, contributor_text])
    print(text_for_author)

    print("** All commits (%d):\n" % len(commits))
    print("\n".join([format_oneline(c) for c in commits.values()]))


if __name__ == '__main__':
    main()
