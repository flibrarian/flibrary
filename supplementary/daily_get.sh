read -p 'ENTER BASE URL: ' base

FAILED=()

list_url="$base"/daily/
response=$(curl -s --retry 3 "$list_url")
regex="(?<=\")(f\.fb2\.\d+-\d+\.zip)(?=\")"
readarray -t archives < <(echo "$response" | grep -oP "$regex")

mkdir -p daily
mkdir -p dailytmp

for archive in "${archives[@]}"; do
	echo $archive >&2
	remote_url="$base/daily/$archive"
	local_file="./daily/$archive"
	response=$(curl -sI --retry 3 "$remote_url")
	http_code=$(echo "$response" | awk 'NR==1 {print $2}' | tr -d '\r')
	if [ "$http_code" -eq 200 ]; then
		remote_size=$(echo "$response" | awk '/[Cc]ontent-[Ll]ength/ { print $2 }' | tr -d '\r')
		if [ -f "$local_file" ]; then
			local_size=$(stat -c%s "$local_file")
		else
			local_size=0
		fi
		if [ "$remote_size" != "$local_size" ]; then
			echo "  UPDATE(${local_size}->${remote_size})" >&2
			if wget --tries=3 -P dailytmp "$remote_url" && unzip -tq "dailytmp/$archive"; then
				mv -f dailytmp/"$archive" daily/"$archive"
				echo "  SUCCESS" >&2
			else
				echo "  FAIL" >&2
				rm -f dailytmp/"$archive"
				FAILED+=("$archive")
			fi
		else
			echo "  ALREADY(${remote_size})" >&2
		fi
	else
		echo "  FAIL(code=$http_code)" >&2
	fi
done


rm -rf dailytmp

if [ ${#FAILED[@]} -ne 0 ]; then
	echo "SOME FAILED: ${FAILED[*]}"
else
	echo "EVERYTHING OK"
fi








