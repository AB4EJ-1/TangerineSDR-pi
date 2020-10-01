# does user want to start over?
   if result.get('csubmit') == "Discard Changes" :
    channellistform = ChannelListForm()
# populate channel settings from config file
    channelcount = parser['channels']['numChannels']
    form = ChannelControlForm()
    form.channelcount.data = channelcount
    rate_list = []
# populate rate capabilities from config file.
# The config file should have been updated from DE sample rate list buffer.
    numRates = parser['datarates']['numRates']
    for r in range(int(numRates)):
      theRate = parser['datarates']['r'+str(r)]
      theTuple = [ str(theRate), int(theRate) ]
      rate_list.append(theTuple)

    form.channelrate.choices = rate_list
    rate1 = int(parser['channels']['datarate'])
    form.channelrate.data = rate1
    form.maxRingbufsize.data = maxringbufsize
    for ch in range(int(channelcount)):
      channelform = ChannelForm()
      channelform.channel_ant  = parser['channels']['p' + str(ch)] 
      channelform.channel_freq = parser['channels']['f' + str(ch)]
      channellistform.channels.append_entry(channelform)

    return render_template('desetup.html',
	  ringbufferPath = ringbufferPath, channelcount = channelcount,
      channellistform = channellistform,
      form = form, status = pageStatus)
