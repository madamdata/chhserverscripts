#!/bin/bash

MTIME=""
POTYPE=""
PONUMBER=""
HELP=""
SEARCHPATH=""

while [[ $# -gt 0 ]]; do
  case $1 in
    -m|--mtime)
      MTIME="$2"
      shift # past argument
      shift # past value
      ;;
    -t|--potype)
      POTYPE="$2"
      shift # past argument
      shift # past value
      ;;
    -n|--ponumber)
      PONUMBER="$2"
      shift # past argument
      shift
      ;;
    --help)
      HELP="help"
      shift
      ;;
    -*|--*)
      echo "Unknown option $1"
      exit 1
      ;;
  esac
done

if [[ -n HELP ]]
then
	echo "-m <days past> -t <rosenberg|wolter>"
fi

if [[ $POTYPE = rosenberg ]]
then
	SEARCHPATH='/home/chh/mail/attachments/rosenberg'
fi 


if [[ $POTYPE = wolter ]]
then
	SEARCHPATH='/home/chh/mail/attachments/wolter'
fi 

if [[ -n $MTIME ]]
then
	echo $MTIME
	find $SEARCHPATH -name '*.xlsx' -mtime "-$MTIME" -exec sh -c "2scraper.py -mode dryrun -potype $POTYPE '{}' && read -p 'continue?' -n 1" \;
fi

if [[ -n $PONUMBER ]]
then
	echo '*$PONUMBER*.xlsx'
	find $SEARCHPATH -name "*$PONUMBER*.xlsx" -exec sh -c "2scraper.py -mode dryrun -potype $POTYPE '{}' && read -p 'continue?' -n 1" \;
fi

