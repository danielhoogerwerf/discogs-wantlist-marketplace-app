## Discogs Wantlist Marketplace App - v0.5
## Made by Daniel Hoogerwerf - https://github.com/danielhoogerwerf/
##
## This program is a hobby project and therefore has no warranty, no support, no license and no complaining :-)
## Use it for fun, at your own risk and please don't use it for production purposes.
##
## Requirements: Python 3, requests and xmltodict libraries.

import requests, json, time, xmltodict, csv, sys
from requests.exceptions import HTTPError
from random import uniform


# Configuration Options
client_token = '' # Fill in here your personal generated Discogs token. Generate one here: https://www.discogs.com/settings/developers
discogsUrl = 'https://api.discogs.com/users/USER/wants' # Change the USER to your discogs user, will fix this in the future.
discogsMarketPlaceUrl = 'https://api.discogs.com/marketplace/listings/' 
discogsRssUrl = 'https://www.discogs.com/sell/release/'
qualityWanted = ['Near Mint (NM or M-)', 'Mint (M)']  # Other options: 'Very Good Plus (VG+)', 'Very Good (VG)', 'Good Plus (G+)', 'Good (G)', 'Fair (F)', ''Generic', 'No Cover', 'Not Graded'
outputFileName = './d-results.csv' # Path of the output CSV
errorFileName = './d-errors.txt' # Path of the error log

# Specify a unique User-Agent, as written in the Discogs API requirements for authenticated requests.
HEADERS = {'User-Agent': 'Test/0.1'}

# User-agent for non authenticated queries.
HEADERS_ANONYMOUS = {'User-Agent': 'Test/0.1'}


### NO EDITING NEEDED BELOW THIS POINT ###
def perform_api_query(url, hdr, auth):
    """
     :param: str, the url, use authentication string or not
     :return: results in json
    """
    for urlName in [url]:
        try:
            # Attach token within header to perform authentication if argument 'True' is supplied.
            if auth:
                response = requests.get(urlName, headers=hdr, params={'token':client_token})
            else:
                response = requests.get(urlName, headers=hdr)
                response.raise_for_status()
        except Exception as err:
            if ['Timeout', 'timeout'] in err:
                with open(errorFileName, 'a+') as f:
                    try:
                        f.write(err)
                    except:
                        True
                print(f'Timeout error occurred: {err}')
                print('Trying again...')  
                time.sleep(10)
            else:
                print(f'Other error occurred: {err}')  
                with open(errorFileName, 'a+') as f:
                    try:
                        f.write(err)
                    except:
                        True
                quit()
        else:
            # Check if we are not over the returned rate limit, so we do not angry Discogs :-)
            availableresults = response.headers['X-Discogs-Ratelimit-Remaining']
            if availableresults <= '1':
                print('Too many API requests performed. waiting for a bit..')
                time.sleep(70)
            return response.json()

def perform_rss_query(url, hdr=HEADERS_ANONYMOUS):
    """
     :param:  url, headers
     :return: results in json
    """
    noTimeout = False
    for urlName in [url]:
        while noTimeout == False:
            try:
                response = requests.get(urlName, headers=hdr)
                response.raise_for_status()
                noTimeout = True
            except HTTPError as http_err:
                print(f'HTTP error occurred: {http_err}')
                quit()
            except Exception as err:
                if ['Timeout', 'timeout'] in err:
                    with open(errorFileName, 'a+') as f:
                        try:
                            f.write(err)
                        except:
                            True
                    print(f'Timeout error occurred: {err}')
                    print('Trying again...')  
                    time.sleep(10)
                else:
                    print(f'Other error occurred: {err}')  
                    with open(errorFileName, 'a+') as f:
                        try:
                            f.write(err)
                        except:
                            True
                    quit()
            else:
                return response.text


def perform_pages_query(url, auths):
    """
     :param: url, use authentication string or not
     :return: results in json
    """
    # If the results are spread over multiple pages, perform multiple URL 
    # lookups to get all the results combined.

    print('Retrieving first results..', end='')
    results = perform_api_query(url, HEADERS, auths)
    print(' Done.')
    try:

        # Check if there are multiple pages within the initial results
        pages = results['pagination']['pages']
        print('Amount of Page URL\'s to download: {}.'.format(pages))
    except KeyError:
        # If not, just return the initial results then
        return results
    else:
        resultList = []

        # Start from page 1, necessary for a correct loop ending.
        amountPages = 1

        # Since we only are interested in the release URL's, filter out the rest here. 
        # This is the initial filtering to have correct results before the loop starts.
        for v in results['wants']:
            resultList.append(v['basic_information']['resource_url'])

        while amountPages < pages:
            u = results['pagination']['urls']['next']

            # Since there is a weird bug that duplicates the auth token parameter in each next page URL 
            # retrieved from the API, let's first clean that up.
            urlFixDup = ''
            stripUrl = u.split('&')

            # This is a neat python trick. Since there cannot be duplicate keys inside a Dict, 
            # python automatically removes the duplicates.
            removeDuplicates = list(dict.fromkeys(stripUrl))

            # Now stitch the URL back together.
            for i in range(len(removeDuplicates)):
                if i != 0:
                    urlFixDup += '&' + removeDuplicates[i]
                else:
                    urlFixDup += removeDuplicates[i]
            
            print('Downloading results from URL: {}&{}..'.format(removeDuplicates[0],removeDuplicates[-1]), end='')
            newResult = perform_api_query(urlFixDup, HEADERS, auths)
            print(' Finished.')

            # Again, filter out the stuff we don't want for the new results.
            for v in newResult['wants']:
                resultList.append(v['basic_information']['resource_url'])
            amountPages += 1
            
            # Let's wait a bit to not hammer the API.
            time.sleep(round(uniform(1.0,1.5),2))
            results = newResult

        print('Wantlist downloaded.\n')
        return resultList


## Main Program
if __name__ == '__main__':

    # Prep CSV file and clean it
    fields = ['Marketplace ID', 'Release ID', 'Release Name', 'Sleeve Condition', 'Vinyl Condition', 'Price', 'Currency']
    print('Cleaning output file {}...'.format(outputFileName.split('/')[-1]), end='')

    with open(outputFileName, 'w+') as f: 
        try:
            csvFile = csv.DictWriter(f, fields, delimiter=',', quoting=csv.QUOTE_NONE, escapechar='\\')
            csvFile.writeheader()
            print(' Done!')
        except Exception as err:
            print(f' Error occured: {err}. Fatal error! Quitting..')
            quit()

    # Start program and get wantlist
    ress = perform_pages_query(discogsUrl,True)

    releaseList = []
    finalOutput = {}
    for v in ress:
        releaseList.append(v.split('/')[-1])

    # Start the loop, go over each release ID, grab the XML and parse the 
    # marketplace URL's for the prices.
    for release in releaseList:
        sellUrl = []
        print('Getting market prices for release {}..'.format(release), end='')
        releaseUrl = discogsRssUrl+release+'?output=rss'
        xmlRaw = perform_rss_query(releaseUrl)
        print(' Done!')
        xmlDict = xmltodict.parse(xmlRaw)

        # Sometimes we miss stuff in the XML. 
        if 'entry' not in xmlDict['feed']:
            continue

        if not isinstance(xmlDict['feed']['entry'], list):
            sellUrl.append(xmlDict['feed']['entry']['id'])
        else:
            for newUrl in xmlDict['feed']['entry']:
                sellUrl.append(newUrl['id'])

        # Obtain price per marketplace ID
        for getPriceUrl in sellUrl:
            marketPlaceId = getPriceUrl.split('/')[-1]
            formMarketPlaceUrl = discogsMarketPlaceUrl + marketPlaceId + '?EUR' # This only works with token authentication
            print('Obtaining price for Marketplace ID {}:'.format(marketPlaceId), end='')
            getPrice = perform_api_query(formMarketPlaceUrl, HEADERS, True)
            sleeveCondition = getPrice['sleeve_condition'] if getPrice['sleeve_condition'] != '' else 'No Cover'
            vinylCondition = getPrice['condition']
            releaseName = getPrice['release']['description'].replace('"', '').replace(',', '').replace('*', '')
            currencyListed = getPrice['price']['currency']
            if sleeveCondition in qualityWanted or vinylCondition in qualityWanted:
                roundedPrice = round(getPrice['price']['value'],2)
                finalOutput.update({marketPlaceId: {'Release ID': release, 'Release Name': releaseName, 'Sleeve Condition': sleeveCondition, 'Vinyl Condition': vinylCondition, 'Price': roundedPrice, 'Currency': currencyListed}})
                print(' {} {}'.format(roundedPrice, currencyListed))
                
                # Let's wait a bit so we don't hammer the API.
                time.sleep(round(uniform(1.0,1.6),2))
            else:
                print(' Not a quality release. Skipping..')
                # Let's wait a bit so we don't hammer the API.
                time.sleep(round(uniform(1.0,1.8),2))
    
        # Write the results to disk
        print('\nWriting results to {}...'.format(outputFileName.split('/')[-1]), end='')
        with open(outputFileName, 'a+') as f:
            try:
                csvFile = csv.DictWriter(f, fields, delimiter=',', quoting=csv.QUOTE_NONE, escapechar='\\')
                for key, value in finalOutput.items():
                    row = {'Marketplace ID': key}
                    row.update(value)
                    csvFile.writerow(row)
                print(' Done!')
            except Exception as err:
                print(f' Error occured: {err}. Fatal error! Quitting..')
                quit()

        print('Going to next release...')
        finalOutput = {}
    
    print('Program finished!')


